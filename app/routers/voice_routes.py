"""The voice edge's HTTP surface: Twilio calls in, TwiML out.

Twilio cannot present a bearer token, so these routes accept either the
platform's bearer token (an operator testing by hand, or a proxy that adds
it) or a valid ``X-Twilio-Signature`` — HMAC-SHA1 over the request URL and
the sorted form parameters, exactly as Twilio computes it, verified with
``TWILIO_AUTH_TOKEN``. With neither, the route answers 401 like every other
``/v1`` path.

Nothing here dials. ``/v1/voice/originate`` returns the request the edge
*would* send while the Twilio settings are absent.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app import auth, config, dispatch, domain
from app.auth import json_object
from app import tenancy
from app.tenancy import Tenant, TenantRefused, resolve_tenant
from app.voice import canonical_status, twilio_client

router = APIRouter(tags=["voice"])


def twilio_signature_valid(url: str, params: Dict[str, Any], signature: str, token: str) -> bool:
    """Twilio's documented request-validation algorithm."""
    if not token or not signature:
        return False
    material = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(token.encode("utf-8"), material.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, str(signature))


async def _form(request: Request) -> Dict[str, Any]:
    """A webhook body: form-encoded from Twilio, or JSON from a hand test."""
    if "application/json" in str(request.headers.get("content-type") or ""):
        return await json_object(request)
    try:
        form = await request.form()
    except Exception as exc:  # noqa: BLE001 - a malformed body is a refusal
        raise HTTPException(status_code=422, detail="webhook body is not readable") from exc
    return {str(key): str(value) for key, value in form.items()}


def tenant_for_number(number: str) -> str:
    """Which brokerage a Twilio number belongs to.

    A webhook carries no bearer token, so the *called number* is the
    principal: ``TENANT_PHONE_NUMBERS`` maps "+10000000000:psi" to a tenant.
    An unmapped number falls back to the platform tenant — never to a value
    the caller put in the form, which would let anyone holding a signature
    name somebody else's brokerage.
    """
    digits = "".join(ch for ch in str(number or "") if ch.isdigit() or ch == "+")
    for mapping in (config.env("TENANT_PHONE_NUMBERS", "") or "").split(","):
        chunk = mapping.strip()
        if not chunk or ":" not in chunk:
            continue
        phone, _, tenant = chunk.partition(":")
        if "".join(ch for ch in phone if ch.isdigit() or ch == "+") == digits and tenant.strip():
            return tenant.strip()
    return str(config.env("PLATFORM_TENANT", "local") or "local")


async def _principal(request: Request) -> Tenant:
    """Bearer token, or a verified Twilio signature. Otherwise 401."""
    signature = str(request.headers.get("x-twilio-signature") or "")
    token = config.TWILIO_AUTH_TOKEN or ""
    if signature:
        params = await _form(request)
        if twilio_signature_valid(str(request.url), params, signature, token):
            tenant_id = tenant_for_number(params.get("To") or params.get("Called") or "")
            return Tenant(tenant_id=tenant_id, name=tenancy.display_name(tenant_id))
        raise HTTPException(status_code=401, detail="invalid Twilio signature")
    try:
        return resolve_tenant(request.headers)
    except TenantRefused as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/v1/voice/status-callback")
async def status_callback(request: Request) -> Dict[str, Any]:
    """A carrier status becomes a workflow transition, keyed by Call SID."""
    tenant = await _principal(request)
    auth.require_permission(tenant, "write")
    form = await _form(request)
    parsed = twilio_client().parse_status_callback(form)
    if not parsed.get("call_sid"):
        raise HTTPException(status_code=422, detail="Missing required field: CallSid")
    transition = dispatch.execute(
        "workflow",
        "transition",
        {
            "call_sid": parsed["call_sid"],
            "event": parsed.get("call_event") or "dial",
            "previous_state": form.get("previous_state") or "queued",
            "language": form.get("language") or "en",
        },
    )
    entry = dispatch.execute(
        "event_bus",
        "append",
        {
            "tenant_id": tenant.tenant_id,
            "call_sid": parsed["call_sid"],
            "event_type": _ledger_event(str(parsed.get("call_status") or "")),
            "detail": parsed,
        },
    )
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "call_sid": parsed["call_sid"],
        "carrier_status": parsed.get("carrier_status"),
        "call_status": parsed.get("call_status"),
        # The carrier said what the call did, so its mapping is the transition;
        # the state table's opinion of it travels beside, not instead.
        "transition_to": parsed.get("transition_to"),
        "guard_allowed": transition.get("transition_allowed"),
        "guard_reason": transition.get("refusal_reason"),
        "ledger": entry.get("entry"),
        "authority": transition.get("authority"),
    }


def _ledger_event(status: str) -> str:
    return {
        "initiated": "initiated",
        "ringing": "ringing",
        "answered": "answered",
        "completed": "call_ended",
        "failed": "attempted",
        "busy": "attempted",
        "no-answer": "attempted",
    }.get(canonical_status(status), "initiated")


@router.post("/v1/voice/gather")
async def gather(request: Request) -> Dict[str, Any]:
    """Speech gathered from the caller, turned into the next spoken turn."""
    tenant = await _principal(request)
    auth.require_permission(tenant, "write")
    form = await _form(request)
    parsed = twilio_client().parse_gather_callback(form)
    # Twilio's <Gather input="speech"> callback carries no Language field, so
    # parsing it alone always answered "en" and an Arabic caller was answered
    # with the English line. The call's own language comes from the voice
    # edge row for this Call SID; an explicit form value still wins.
    language = str(form.get("language") or "")[:2].lower()
    if language not in ("en", "ar"):
        language = ""
        try:
            from app import store

            rows = [
                row
                for row in store.list_all("voice_gateway", tenant.tenant_id)
                if str(row.get("call_sid") or "") == str(parsed.get("call_sid") or "")
            ]
            if rows:
                language = str(rows[-1].get("language") or "")[:2].lower()
        except Exception:  # noqa: BLE001 -- fall back below
            language = ""
    if language not in ("en", "ar"):
        language = parsed.get("language") or "en"
    response = dispatch.execute(
        "llm_enhancer",
        "turn",
        {
            "tenant_id": tenant.tenant_id,
            "call_sid": parsed.get("call_sid"),
            "language": language,
            "project_tag": form.get("project_tag"),
            "utterance": parsed.get("asr_transcript"),
            "claim_type": form.get("claim_type"),
        },
    )
    return {"ok": True, "tenant": tenant.to_dict(), **response}


@router.post("/v1/voice/whisper")
async def whisper(request: Request) -> PlainTextResponse:
    """The private whisper TwiML — spoken to the broker leg only."""
    tenant = await _principal(request)
    form = await _form(request)
    twiml = twilio_client().whisper_twiml(
        {
            "broker_language": form.get("broker_language") or "en",
            "whisper_text": form.get("whisper_text") or form.get("summary") or "",
        }
    )
    return PlainTextResponse(twiml, media_type="application/xml")


@router.post("/v1/voice/originate")
async def originate(request: Request) -> Dict[str, Any]:
    """Place the outbound call, inside the campaign's pacing policy.

    The cap and the call window are checked here, not only in the console:
    a token holder with the dialling opt-in should not be able to bypass the
    policy the operator set for the campaign. The answer and status-callback
    URLs come from settings — a caller who could name them could point the
    carrier at anything.
    """
    tenant = await _principal(request)
    auth.require_permission(tenant, "write")
    form = await _form(request)
    if not form.get("to_number"):
        raise HTTPException(status_code=422, detail="Missing required field: to_number")
    language = str(form.get("language") or "en")[:2]
    permitted = domain.dial_permitted(tenant.tenant_id, language=language)
    if not permitted["permitted"]:
        raise HTTPException(status_code=409, detail=permitted["reason"])
    record = {
        "call_sid": form.get("call_sid") or "",
        "to_number": form.get("to_number"),
        "voice_action": "originate",
        "language": language,
        "reference": form.get("reference") or tenant.tenant_id,
        "status": "open",
        "tenant_id": tenant.tenant_id,
        "answer_url": permitted["answer_url"],
        "status_callback_url": permitted["status_callback_url"],
    }
    from app import store
    from app.actions import handle_for
    from app.models import MODELS

    outcome = handle_for("voice_gateway").handle(record)
    # The route persists, so the attempt is countable: dial_permitted reads
    # today's originate rows back to enforce DAILY_CALL_CAP. Without this the
    # cap was advertised in the pacing answer and enforced nowhere -- the
    # three-hundredth dial of the day was permitted exactly like the first.
    emitted = outcome.get("record") if isinstance(outcome, dict) else None
    attempt = dict(record)
    if isinstance(emitted, dict):
        attempt.update({key: value for key, value in emitted.items() if value is not None})
    attempt["call_sid"] = str(outcome.get("call_sid") or record.get("call_sid") or "") if isinstance(outcome, dict) else str(record.get("call_sid") or "")
    attempt["voice_action"] = "originate"
    attempt["tenant_id"] = tenant.tenant_id
    store.save(
        "voice_gateway",
        {key: value for key, value in attempt.items() if key in MODELS["voice_gateway"].FIELDS},
        tenant.tenant_id,
    )
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "pacing": permitted["pacing"],
        "result": outcome,
    }


@router.get("/v1/voice/edge")
def edge_state(request: Request) -> Dict[str, Any]:
    """Whether the Twilio edge is connected, and what is missing if not."""
    resolve_tenant_or_401 = auth.resolve_principal(request)
    return {
        "ok": True,
        "tenant": resolve_tenant_or_401.to_dict(),
        "edge": twilio_client().state(),
        "statuses": sorted(config.TWILIO_ASR_LANGUAGE),
    }
