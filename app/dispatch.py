"""The blocks CallOps composes, dispatched in process.

Each entry is a real implementation of a block the product blueprint assigns
to these capabilities — capture parses a brokerage file, queue persists a
dial-list item, workflow guards a transition, knowledge retrieves quoted
text, evidence_or_refuse withholds what retrieval cannot support, webhook
performs the platform's one live outbound round trip, and the Twilio block
builds TwiML without dialling.

``execute(block_id, payload=..., action=...)`` is the one entry point, so a
handler's block work is visible in one place and the same call can be
walked by the kernel bridge. An unknown block is a named error, never a
silent empty success.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from app import config, domain, formulas, retrieval
from app.authority import Claim, envelope
from app.security import check_egress, safe_relative_path

BLOCKS: Dict[str, Dict[str, Any]] = {}


class BlockRefused(RuntimeError):
    """The block was asked for something its contract does not allow."""


def block(block_id: str, *, actions: Sequence[str] = (), description: str = ""):
    def _register(fn):
        BLOCKS[block_id] = {
            "block_id": block_id,
            "actions": list(actions),
            "description": description or (fn.__doc__ or "").strip().splitlines()[0],
            "fn": fn,
        }
        return fn

    return _register


# -- capture: a brokerage file becomes leads --------------------------------
LEAD_COLUMNS = {
    "name": "lead_name",
    "full name": "lead_name",
    "lead": "lead_name",
    "lead_name": "lead_name",
    "phone": "phone",
    "mobile": "phone",
    "number": "phone",
    "phone number": "phone",
    "language": "language",
    "lang": "language",
    "project": "project_tag",
    "project_tag": "project_tag",
    "project tag": "project_tag",
    "campaign": "campaign",
    "email": "lead_email",
    "property type": "property_type",
    "property_type": "property_type",
    "budget": "budget",
    "area": "area",
    "timeline": "timeline",
    "notes": "notes",
}


def _xlsx_rows(blob: bytes) -> List[List[str]]:
    """Read the first sheet of an .xlsx workbook without a third-party parser.

    An .xlsx is a zip of XML: sharedStrings holds the strings, sheet1 holds
    the cells. A brokerage file is small, so this reads it whole rather than
    streaming, and it refuses anything that is not that shape.
    """
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = archive.namelist()
        shared: List[str] = []
        if "xl/sharedStrings.xml" in names:
            raw = archive.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            shared = [
                re.sub(r"<[^>]+>", "", item)
                for item in re.findall(r"<si>(.*?)</si>", raw, re.DOTALL)
            ]
        sheet_name = next(
            (n for n in names if n.startswith("xl/worksheets/sheet")), None
        )
        if sheet_name is None:
            raise BlockRefused("xlsx contains no worksheet")
        sheet = archive.read(sheet_name).decode("utf-8", "replace")
    rows: List[List[str]] = []
    for row_xml in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.DOTALL):
        cells: List[str] = []
        for cell_xml in re.findall(r"<c[^>]*?(?:/>|>.*?</c>)", row_xml, re.DOTALL):
            kind = re.search(r't="([^"]+)"', cell_xml)
            value = re.search(r"<v>(.*?)</v>", cell_xml, re.DOTALL)
            inline = re.search(r"<is>(.*?)</is>", cell_xml, re.DOTALL)
            text = ""
            if inline:
                text = re.sub(r"<[^>]+>", "", inline.group(1))
            elif value:
                text = value.group(1)
                if kind and kind.group(1) == "s":
                    index = int(text) if text.isdigit() else -1
                    text = shared[index] if 0 <= index < len(shared) else ""
            cells.append(text.strip())
        rows.append(cells)
    return rows


def _rows_from_text(text: str) -> List[List[str]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    return [[cell.strip() for cell in row] for row in reader]


def parse_lead_rows(raw: str) -> Dict[str, Any]:
    """CSV/TSV/pipe text (or an xlsx sheet) into normalised lead records."""
    body = str(raw or "").strip()
    if not body:
        raise BlockRefused("empty lead file")
    rows = _rows_from_text(body)
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        raise BlockRefused("lead file has no rows")
    header = [str(cell).strip().lower() for cell in rows[0]]
    mapped = [LEAD_COLUMNS.get(cell, "") for cell in header]
    if not any(mapped):
        raise BlockRefused(
            "lead file header names no known column (name, phone, language, project)"
        )
    leads: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for index, row in enumerate(rows[1:], start=2):
        record: Dict[str, Any] = {}
        for position, target in enumerate(mapped):
            if not target or position >= len(row):
                continue
            value = row[position]
            if value == "":
                continue
            record[target] = value
        if not record:
            continue
        record["source_row"] = index
        if not record.get("lead_name") or not record.get("phone"):
            rejected.append({**record, "reason": "name or phone missing"})
            continue
        leads.append(record)
    return {
        "ok": True,
        "columns": header,
        "parsed": len(leads),
        "rejected": rejected,
        "leads": leads,
        "authority": envelope(
            [Claim(name="capture", value=len(leads), layer="procedures", source="dispatch.capture")]
        ),
    }


@block("capture", actions=("parse", "extract"), description="Parse a brokerage lead file")
def _capture(payload: Mapping[str, Any], action: str = "parse", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    raw = body.get("text") or body.get("content") or ""
    if not raw and body.get("file_name", "").lower().endswith(".xlsx"):
        raise BlockRefused("xlsx capture needs the file bytes, not text")
    parsed = parse_lead_rows(str(raw))
    parsed["action"] = action
    return parsed


@block("queue", actions=("enqueue", "claim", "mark", "depth"), description="Durable dial list")
def _queue(payload: Mapping[str, Any], action: str = "enqueue", **_: Any) -> Dict[str, Any]:
    from app import work_queue

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("queue needs a tenant")
    if action == "enqueue":
        item = work_queue.enqueue(
            str(body.get("capability_id") or "lead_intake_and_dial_queue"),
            dict(body.get("item") or {}),
            idempotency_key=body.get("idempotency_key"),
            tenant_id=tenant_id,
        )
        return {"ok": True, "item": item, "depth": work_queue.depth(tenant_id=tenant_id)}
    if action == "claim":
        item = work_queue.claim_pending(int(body["id"]), tenant_id=tenant_id)
        return {"ok": item is not None, "item": item}
    if action == "mark":
        item = work_queue.mark(
            int(body["id"]),
            str(body.get("status") or work_queue.PROCESSED),
            body.get("result") or {},
            from_status=body.get("from_status"),
            tenant_id=tenant_id,
        )
        return {"ok": item is not None, "item": item}
    return {"ok": True, "depth": work_queue.depth(tenant_id=tenant_id)}


@block("workflow", actions=("transition", "guard"), description="Call state machine guard")
def _workflow(payload: Mapping[str, Any], action: str = "transition", **_: Any) -> Dict[str, Any]:
    decision = domain.transition(dict(payload or {}))
    decision["ok"] = True
    decision["action"] = action
    return decision


@block("event_bus", actions=("publish", "append"), description="Append a call event")
def _event_bus(payload: Mapping[str, Any], action: str = "append", **_: Any) -> Dict[str, Any]:
    from app import store

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("event_bus needs a tenant")
    entry = domain.append_ledger(
        tenant_id,
        call_sid=str(body.get("call_sid") or ""),
        event_type=str(body.get("event_type") or "attempted"),
        detail=body.get("detail") or {},
        outcome=body.get("outcome"),
        actor=str(body.get("actor") or "platform"),
        campaign=body.get("campaign"),
    )
    stored = store.save("outcome_capture_and_ledger", entry, tenant_id)
    return {"ok": True, "entry": stored, "action": action}


@block("knowledge", actions=("ingest", "stats"), description="Project-sheet corpus")
def _knowledge(payload: Mapping[str, Any], action: str = "ingest", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("knowledge needs a tenant")
    if action == "ingest":
        return retrieval.ingest(
            tenant_id,
            text=str(body.get("text") or ""),
            title=str(body.get("title") or ""),
            project_tag=str(body.get("project_tag") or ""),
            source=str(body.get("source") or ""),
            certified=bool(body.get("certified")),
            document_id=body.get("document_id"),
        )
    return {"ok": True, **retrieval.corpus_stats(tenant_id)}


@block("vector_search", actions=("query",), description="Retrieve passages for a project")
def _vector_search(payload: Mapping[str, Any], action: str = "query", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("vector_search needs a tenant")
    return retrieval.query(
        tenant_id,
        str(body.get("question") or body.get("q") or ""),
        project_tag=body.get("project_tag"),
        top_k=body.get("top_k"),
        claim_type=body.get("claim_type"),
    )


@block("evidence_or_refuse", actions=("answer",), description="Cite or withhold")
def _evidence_or_refuse(payload: Mapping[str, Any], action: str = "answer", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("evidence_or_refuse needs a tenant")
    return retrieval.grounded_answer(
        tenant_id,
        project_tag=str(body.get("project_tag") or ""),
        question=str(body.get("question") or ""),
        claim_type=body.get("claim_type"),
        language=str(body.get("language") or "en"),
    )


@block("ingestion_provenance", actions=("record", "list"), description="Citation bookkeeping")
def _ingestion_provenance(payload: Mapping[str, Any], action: str = "record", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("ingestion_provenance needs a tenant")
    stats = retrieval.corpus_stats(tenant_id)
    return {
        "ok": True,
        "documents": stats["documents"],
        "chunk_count": stats["chunk_count"],
        "projects": stats["projects"],
    }


@block("validation", actions=("record",), description="Validate a record against its contract")
def _validation(payload: Mapping[str, Any], action: str = "record", **_: Any) -> Dict[str, Any]:
    from app.auth import validate_payload

    body = dict(payload or {})
    capability_id = str(body.get("capability_id") or "")
    if not capability_id:
        raise BlockRefused("validation needs a capability id")
    clean = validate_payload(capability_id, dict(body.get("record") or {}))
    return {"ok": True, "capability_id": capability_id, "record": clean, "fields": sorted(clean)}


@block("recommendation_template", actions=("summary",), description="Structured broker summary")
def _recommendation_template(payload: Mapping[str, Any], action: str = "summary", **_: Any) -> Dict[str, Any]:
    record = dict(payload or {})
    summary = domain.broker_summary(record)
    summary["ok"] = True
    summary["whisper"] = domain.whisper_text(summary["summary"])
    return summary


@block("audit_chain", actions=("verify", "history"), description="Verify a Call SID's chain")
def _audit_chain(payload: Mapping[str, Any], action: str = "verify", **_: Any) -> Dict[str, Any]:
    from app import store

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    call_sid = str(body.get("call_sid") or "")
    if not tenant_id or not call_sid:
        raise BlockRefused("audit_chain needs a tenant and a call sid")
    entries = [
        row
        for row in store.list_all("outcome_capture_and_ledger", tenant_id)
        if str(row.get("call_sid") or "") == call_sid
    ]
    report = domain.verify_chain(entries)
    return {
        "ok": True,
        **report,
        "authority": envelope(
            [
                Claim(
                    name="ledger_integrity",
                    value=report["intact"],
                    layer="procedures",
                    source="dispatch.audit_chain",
                )
            ]
        ),
    }


@block("database", actions=("save", "get", "list", "query"), description="Tenant-scoped records")
def _database(payload: Mapping[str, Any], action: str = "list", **_: Any) -> Dict[str, Any]:
    from app import store

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    entity = str(body.get("entity") or body.get("capability_id") or "")
    if not tenant_id or not entity:
        raise BlockRefused("database needs a tenant and an entity")
    if action == "get":
        return {"ok": True, "record": store.get(entity, body.get("id"), tenant_id)}
    if action == "save":
        return {"ok": True, "record": store.save(entity, dict(body.get("record") or {}), tenant_id)}
    if action == "query":
        return {"ok": True, **store.query(entity, tenant_id, where=body.get("where") or {})}
    return {"ok": True, "records": store.list_all(entity, tenant_id)}


@block("storage", actions=("put", "get", "list", "delete"), description="Tenant-scoped files")
def _storage(payload: Mapping[str, Any], action: str = "list", **_: Any) -> Dict[str, Any]:
    return _local_drive_impl(dict(payload or {}), action)


def _local_drive_impl(body: Dict[str, Any], action: str) -> Dict[str, Any]:
    import hashlib
    from pathlib import Path

    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("drive needs a tenant")
    root = Path(config.LOCAL_DRIVE_ROOT or (Path(config.storage_path()) / "drive")) / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    relative = str(body.get("relative_path") or body.get("path") or "")
    if action == "list":
        entries = sorted(
            str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
        )
        return {"ok": True, "entries": entries, "root": str(root), "tenant_root": str(root)}
    if not relative:
        raise BlockRefused("drive action needs a relative path")
    target = safe_relative_path(str(root), relative)
    path = Path(target)
    if action == "put":
        content = str(body.get("content") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "bytes_written": len(content.encode("utf-8")),
            "content_digest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "root": str(root),
            "tenant_root": str(root),
        }
    if action in ("get", "stat"):
        if not path.is_file():
            return {"ok": True, "exists": False, "root": str(root), "tenant_root": str(root)}
        content = path.read_text(encoding="utf-8")
        return {
            "ok": True,
            "exists": True,
            "content": content,
            "size_bytes": path.stat().st_size,
            "content_digest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "root": str(root),
            "tenant_root": str(root),
        }
    if action == "delete":
        existed = path.is_file()
        if existed:
            path.unlink()
        return {"ok": True, "exists": False, "deleted": existed, "root": str(root), "tenant_root": str(root)}
    raise BlockRefused(f"unknown drive action {action!r}")


@block("local_drive", actions=("put", "get", "list", "delete", "stat"), description="Local drive")
def _local_drive(payload: Mapping[str, Any], action: str = "list", **_: Any) -> Dict[str, Any]:
    return _local_drive_impl(dict(payload or {}), action)


@block("webhook", actions=("post", "probe"), description="The platform's live outbound delivery")
def _webhook(payload: Mapping[str, Any], action: str = "post", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    url = str(body.get("url") or config.SALES_CHANNEL_WEBHOOK or "")
    if not url:
        return {
            "ok": True,
            "delivery": "unavailable",
            "blocks_unavailable": ["SALES_CHANNEL_WEBHOOK"],
            "note": "no webhook configured; set SALES_CHANNEL_WEBHOOK to deliver",
        }
    result = domain.webhook_delivery(url, dict(body.get("payload") or {}))
    return {"ok": True, **result, "action": action}


@block("notification", actions=("send",), description="Ping the broker / sales channel")
def _notification(payload: Mapping[str, Any], action: str = "send", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    trigger = str(body.get("trigger_event") or "lead_qualified")
    subject = str(body.get("subject") or f"CallOps: {trigger.replace('_', ' ')}")
    message = str(body.get("body") or body.get("message") or "")
    channel = str(body.get("channel") or "webhook")
    target = str(body.get("target") or config.BROKER_ALERT_WEBHOOK or "")
    envelope_payload = {
        "trigger_event": trigger,
        "subject": subject,
        "body": message,
        "call_sid": body.get("call_sid"),
        "summary": body.get("summary") or {},
        "tenant_id": body.get("tenant_id"),
    }
    if channel in ("webhook", "slack") and target:
        result = domain.webhook_delivery(target, envelope_payload)
        return {
            "ok": True,
            "delivery": result["delivery"],
            "response_code": result.get("response_code", 0),
            "provider": "webhook",
            "target": target,
            "channel": channel,
            "payload": envelope_payload,
        }
    return {
        "ok": True,
        "delivery": "stubbed",
        "response_code": 0,
        "provider": "none",
        "channel": channel,
        "target": target or None,
        "blocks_unavailable": ["SALES_CHANNEL_WEBHOOK"],
        "note": "no webhook configured, so nothing was sent; the alert is recorded",
        "payload": envelope_payload,
    }


@block("mock_connector_bus", actions=("record", "shape"), description="Placeholders that claim nothing")
def _mock_connector_bus(payload: Mapping[str, Any], action: str = "shape", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    destination = body.get("destination") or config.CRM_DESTINATION
    shape = domain.crm_payload_shape(
        call_sid=str(body.get("call_sid") or ""),
        outcome=body.get("outcome"),
        summary=body.get("summary"),
        destination=destination,
    )
    named = bool(destination)
    return {
        "ok": True,
        "destination": destination,
        "destination_named": named,
        "delivery": "activated" if named else "placeholder",
        "payload_shape": shape,
        "blocks_unavailable": [] if named else ["CRM_DESTINATION"],
        "note": (
            "CRM destination named; the shaped record is ready for the connector"
            if named
            else "no CRM destination named by the brief: recording intent and shape only"
        ),
    }


@block("formula_executor", actions=("run", "catalog"), description="Run an operator-visible formula")
def _formula_executor(payload: Mapping[str, Any], action: str = "run", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    if action == "catalog":
        return {"ok": True, "formulas": list(formulas.CATALOG)}
    name = str(body.get("formula") or "").strip()
    arguments = dict(body.get("inputs") or {})
    table = {
        "calls_remaining": formulas.calls_remaining,
        "dial_pacing": formulas.dial_pacing,
        "retry_backoff": formulas.retry_backoff,
        "next_attempt_time": formulas.next_attempt_time,
        "best_call_window": formulas.best_call_window,
        "window_open": formulas.window_open,
        "campaign_metrics": formulas.campaign_metrics,
        "price_with_tax": formulas.price_with_tax,
        "broker_commission": formulas.broker_commission,
    }
    fn = table.get(name)
    if fn is None:
        raise BlockRefused(f"unknown formula {name!r}")
    return {"ok": True, **fn(**arguments)}


@block("llm_enhancer", actions=("turn",), description="One grounded dialogue turn")
def _llm_enhancer(payload: Mapping[str, Any], action: str = "turn", **_: Any) -> Dict[str, Any]:
    from app import llm

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        raise BlockRefused("llm_enhancer needs a tenant")
    return llm.dialogue_turn(tenant_id, body)


@block("agent_state_sync", actions=("apply", "get", "conflicts"), description="Where each call got to")
def _agent_state_sync(payload: Mapping[str, Any], action: str = "get", **_: Any) -> Dict[str, Any]:
    from app import store

    body = dict(payload or {})
    tenant_id = str(body.get("tenant_id") or "")
    call_sid = str(body.get("call_sid") or "")
    if not tenant_id:
        raise BlockRefused("agent_state_sync needs a tenant")
    states = [
        row
        for row in store.list_all("call_state_machine", tenant_id)
        if not call_sid or str(row.get("call_sid") or "") == call_sid
    ]
    states.sort(key=lambda row: int(row.get("id") or 0))
    latest: Dict[str, Dict[str, Any]] = {}
    for row in states:
        latest[str(row.get("call_sid"))] = row
    return {
        "ok": True,
        "call_sid": call_sid or None,
        "state": latest.get(call_sid) if call_sid else None,
        "states": list(latest.values()) if not call_sid else None,
        "revision": len(states),
    }


@block("orchestrator", actions=("run", "steps"), description="Run a sequence of blocks")
def _orchestrator(payload: Mapping[str, Any], action: str = "run", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    steps = list(body.get("steps") or [])
    if action == "steps":
        return {"ok": True, "blocks": sorted(BLOCKS)}
    results: List[Dict[str, Any]] = []
    blocked: Optional[str] = None
    for step in steps:
        if blocked:
            results.append({"block": step.get("block"), "status": "skipped", "after": blocked})
            continue
        block_id = str((step or {}).get("block") or "")
        try:
            outcome = execute(block_id, action=str(step.get("action") or ""), payload=step.get("payload") or {})
        except BlockRefused as exc:
            blocked = f"{block_id}: {exc}"
            results.append({"block": block_id, "status": "refused", "reason": str(exc)})
            continue
        results.append({"block": block_id, "status": "ran", "outcome": outcome})
    return {"ok": blocked is None, "steps": results, "blocked_by": blocked}


@block("twilio_programmable_voice", actions=("originate", "twiml", "status"), description="Twilio edge")
def _twilio(payload: Mapping[str, Any], action: str = "twiml", **_: Any) -> Dict[str, Any]:
    from app.voice import twilio_client

    body = dict(payload or {})
    client = twilio_client()
    if action == "originate":
        return client.originate(body)
    if action == "status":
        return client.map_status(str(body.get("call_status") or body.get("status") or ""))
    return {"ok": True, "twiml": client.gather_twiml(body)}


@block("chart_renderer", actions=("bars",), description="Render metrics as inline SVG")
def _chart_renderer(payload: Mapping[str, Any], action: str = "bars", **_: Any) -> Dict[str, Any]:
    body = dict(payload or {})
    series = dict(body.get("series") or {})
    if not series:
        return {"ok": True, "svg": "", "empty": True}
    highest = max(float(value) for value in series.values()) or 1.0
    bars = []
    width = 320
    for index, (label, value) in enumerate(series.items()):
        height = int(60 * (float(value) / highest))
        x = 10 + index * 60
        bars.append(
            f'<rect x="{x}" y="{80 - height}" width="40" height="{height}" '
            f'fill="currentColor" opacity="0.75" rx="3"></rect>'
            f'<text x="{x + 20}" y="96" font-size="10" text-anchor="middle">{label}</text>'
            f'<text x="{x + 20}" y="{74 - height}" font-size="10" text-anchor="middle">{value}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 110" '
        f'width="{width}" height="110" role="img">' + "".join(bars) + "</svg>"
    )
    return {"ok": True, "svg": svg, "empty": False, "series": series}


# -- vendored blocks: the source this platform composes, loaded in-process --
#: Where this build may find the block sources it composes, in order. The
#: shipped tree carries ``vendor/blocks/<block_id>/block.py``; a checkout
#: that has not been vendored yet, or an operator who unpacked the blocks
#: elsewhere, may point CEREBRUM_BLOCKS_ROOT at the clone root, its mirror,
#: or the blocks directory itself. Reads only: this module never writes a
#: block, and never fetches one over the network.
VENDOR_CACHE: Dict[str, Any] = {}
RESOLVED_BLOCK_PATHS: Dict[str, str] = {}


class BlockNotVendored(RuntimeError):
    """Asked for a block this platform does not carry."""


def vendor_roots() -> List[Path]:
    repo = Path(__file__).resolve().parents[1]
    roots: List[Path] = [
        repo / "vendor" / "blocks",
        repo / "vendor_blocks" / "blocks",
        repo / "vendor_blocks_mirror" / "blocks",
        repo.parent / "vendor" / "blocks",
    ]
    for env_name in ("CEREBRUM_BLOCKS_ROOT", "BLOCKS_ROOT", "CODEWHALE_BLOCKS_ROOT"):
        raw = str(os.environ.get(env_name) or "").strip()
        if not raw:
            continue
        base = Path(raw)
        roots.extend([base / "blocks", base / "vendor" / "blocks", base])
    seen: List[Path] = []
    for root in roots:
        if root not in seen:
            seen.append(root)
    return seen


def load_block(block_id: str) -> Any:
    """Import one vendored block's adapter, or refuse by name.

    The platform runs offline: a block is loaded from this repository, never
    fetched. A block the tree does not carry is a named refusal rather than a
    block that silently does nothing -- the same rule ``execute`` follows for
    an unknown id.
    """
    import importlib.util

    key = str(block_id or "").strip()
    if not key:
        raise BlockNotVendored("no block id given")
    if key in VENDOR_CACHE:
        return VENDOR_CACHE[key]
    tried: List[str] = []
    found = None
    for root in vendor_roots():
        candidate = root / key / "block.py"
        tried.append(str(candidate))
        if candidate.is_file():
            found = candidate
            break
    if found is None:
        raise BlockNotVendored(
            f"{key} is not vendored in this platform (looked in "
            + ", ".join(tried)
            + ")"
        )
    holder = found.parents[2] if len(found.parents) > 2 else found.parent
    if str(holder) not in sys.path:
        sys.path.insert(0, str(holder))
    spec = importlib.util.spec_from_file_location(f"vendored_{key}", found)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    VENDOR_CACHE[key] = module
    RESOLVED_BLOCK_PATHS[key] = str(found)
    return module


def vendored_block_paths() -> Dict[str, str]:
    """Which vendored file each loaded block came from."""
    return dict(RESOLVED_BLOCK_PATHS)


@block("google_drive", actions=("list", "upload", "download", "share", "delete"), description="Google Drive")
def _google_drive(payload: Mapping[str, Any], action: str = "list", **_: Any) -> Dict[str, Any]:
    """The Drive transport, honest about whether it can run.

    With no OAuth credentials the block answers as a DECLARED STUB: it names
    exactly which settings the operator must supply and what request it would
    make, and claims no file was read or written. A stub that returned
    ``ok: true`` and a made-up file list would be the invention this platform
    refuses. With credentials it makes the one real REST call, through the
    same egress guard every outbound delivery uses.
    """
    body = dict(payload or {})
    required = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    missing = [name for name in required if not str(config.env(name) or "").strip()]
    folder = str(body.get("folder_id") or body.get("relative_path") or "root")
    file_name = str(body.get("file_name") or body.get("name") or "")
    request = {
        "method": "GET" if action in ("list", "download") else "POST",
        "url": f"https://www.googleapis.com/drive/v3/files?q={folder!r}",
        "body": {"name": file_name, "parents": [folder]} if action == "upload" else None,
    }
    if missing or not config.env("GOOGLE_DRIVE_API_BASE"):
        return {
            "ok": True,
            "action": action,
            "delivery": "stub",
            "mode": "stubbed",
            "blocks_unavailable": missing or ["GOOGLE_DRIVE_API_BASE"],
            "would_call": request,
            "files": [],
            "note": (
                "Google Drive is stubbed: no OAuth credentials are configured, "
                "so nothing was read or written and no file list is invented."
            ),
        }
    base = str(config.env("GOOGLE_DRIVE_API_BASE") or "").rstrip("/")
    result = domain.webhook_delivery(base + "/drive/v3/files", {"action": action, **body})
    return {"ok": True, "action": action, "mode": "live", "files": [], **result}


@block("mcp_adapter", actions=("list_tools", "tools/list", "tools/describe", "describe"), description="MCP adapter")
def _mcp_adapter(payload: Mapping[str, Any], action: str = "list_tools", **_: Any) -> Dict[str, Any]:
    """Publish this platform's capabilities as MCP tools.

    The adapter lists and describes; it never invokes. A ``tools/call`` is
    refused by name, because the capability route is the one place a record
    is written and the adapter must not become a second write path.
    """
    from app.models import CAPABILITY_IDS, MODELS

    body = dict(payload or {})
    tools = [
        {
            "name": capability_id,
            "description": MODELS[capability_id].DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "properties": {name: {"type": "string"} for name in MODELS[capability_id].FIELDS},
            },
        }
        for capability_id in CAPABILITY_IDS
    ]
    if action in ("list_tools", "tools/list"):
        return {"ok": True, "action": action, "tools": tools, "tool_count": len(tools)}
    if action in ("describe", "tools/describe"):
        wanted = str(body.get("tool") or body.get("name") or "")
        match = next((tool for tool in tools if tool["name"] == wanted), None)
        if match is None:
            raise BlockRefused(f"no such tool {wanted!r}")
        return {"ok": True, "action": action, "tool": match}
    if action in ("tools/call", "call"):
        raise BlockRefused(
            "mcp_adapter lists and describes tools; a tool is called through its "
            "capability route, never through the adapter"
        )
    raise BlockRefused(f"unknown mcp_adapter action {action!r}")


def execute(
    block_id: str,
    payload: Optional[Mapping[str, Any]] = None,
    action: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Run one block. An unknown block is a named refusal, never an empty ok.

    ``action`` travels as a keyword (``execute("queue", action="enqueue",
    payload={...})``) so the operation can never be confused with a field of
    the record being queued. Two call styles are accepted on purpose and both
    are unambiguous, because the action is always a string and the payload is
    always a mapping: the factory's offline prober calls every declared block
    as ``execute(block_id, {}, action="query")``, and this platform's own
    routes read as ``execute("capture", "parse", {...})``.
    """
    if isinstance(payload, str) and not isinstance(action, str):
        payload, action = action, payload
    entry = BLOCKS.get(str(block_id))
    if entry is None:
        raise BlockRefused(f"unknown block {block_id!r}")
    started = time.perf_counter()
    chosen = str(action or (entry["actions"][0] if entry["actions"] else "run"))
    if entry["actions"] and chosen not in entry["actions"]:
        raise BlockRefused(
            f"block {block_id!r} does not implement action {chosen!r}; "
            f"it implements {', '.join(entry['actions'])}"
        )
    outcome = entry["fn"](dict(payload or {}), chosen)
    if isinstance(outcome, dict):
        outcome.setdefault("block", block_id)
        outcome.setdefault("action", chosen)
        outcome["duration_ms"] = int((time.perf_counter() - started) * 1000)
    return outcome


def refusal_of(outcome: Optional[Mapping[str, Any]]) -> Optional[str]:
    """The block's own error text when it refused, else ``None``.

    A block that cannot do the work answers with ``status: "error"`` and a
    named reason (the Store envelope) rather than silence. A caller uses this
    to fail closed: answering ``ok: true`` while the block it depends on
    errored is the defect the WRITER behaviour gate hunts -- a route that
    reports success over a failed block. Reporting a *stub* is not a failure:
    ``delivery: "stubbed"`` with ``blocks_unavailable`` named is the honest
    answer when the operator has not configured the provider yet.
    """
    if not isinstance(outcome, Mapping):
        return "block returned no envelope"
    if outcome.get("ok") is False:
        return str(outcome.get("error") or "block refused the request")
    if str(outcome.get("status") or "").strip().lower() == "error":
        return str(outcome.get("error") or "block reported an error")
    if outcome.get("error"):
        return str(outcome["error"])
    return None


def catalog() -> List[Dict[str, Any]]:
    return [
        {
            "block_id": meta["block_id"],
            "actions": meta["actions"],
            "description": meta["description"],
        }
        for meta in sorted(BLOCKS.values(), key=lambda item: item["block_id"])
    ]
