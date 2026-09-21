"""Handler for capability notification.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Pings the broker / sales channel the moment a lead qualifies. The vendored
``notification`` block owns delivery (email when a real address is present,
in-process MCP otherwise); the same moment is published on the vendored
``event_bus`` so the dashboard and analytics see it without polling the
notification outbox.

The event bus child is constructed here, fully prepared: topic, a dict
payload, a message, ``channel=mcp`` and the MCP target are all literal, so no
caller ever has to know the event-bus contract and no unprepared child ever
reaches the pipeline.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``notification`` table, through the
       route's tenant-scoped save).
WRITES app.dispatch.execute() results; one notification on the configured
       channel; one ``notification.queued`` event; exactly one row in
       ``notification`` via the ROUTE's ``store.save(entity, record,
       tenant_id)`` -- this handler has no tenant and never persists
       directly.
NEVER  unguarded network egress; a notification with no recipient and no
       channel; ``vendor/**`` (sealed, read-only); another capability's
       table; ``tests/**``.

SMTP settings (``SMTP_HOST``, ``SMTP_PORT``, ``SMTP_USERNAME``,
``SMTP_PASSWORD``, ``NOTIFY_FROM``) are read from the environment with no
defaults; without them a mail channel falls back to in-process MCP delivery
and the record says which channel was actually used.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner, probe_block
from app.security import InputRefused, clean_text

CAPABILITY_ID = "notification"
ENTITY = "notification"
BLOCK_IDS = ['notification', 'event_bus']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'notification': 'send', 'event_bus': 'publish'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'channel', 'recipient', 'subject', 'message',
    'trigger_event', 'delivery_state', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'channel': {'allowed_values': ['email', 'sms', 'mcp', 'webhook'], 'required': True},
    'trigger_event': {'allowed_values': ['lead_qualified', 'transfer_completed',
                                         'call_failed', 'campaign_summary'],
                      'required': True},
}

#: Which notification belongs to which trigger. The vocabulary decides it.
TRIGGER_SUBJECTS = {
    'lead_qualified': "Lead qualified",
    'transfer_completed': "Warm transfer bridged",
    'call_failed': "Call failed",
    'campaign_summary': "Campaign summary",
}


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "notification"
        channel = _text(data, "channel", 20).lower() or "mcp"
        recipient = _text(data, "recipient", 320)
        subject = _text(data, "subject", 200)
        message = _text(data, "message", 2000)
        trigger = _text(data, "trigger_event", 40).lower()
        if channel not in EDGE_CONSTRAINTS['channel']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "channel must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['channel']['allowed_values']),
            }
        if trigger not in TRIGGER_SUBJECTS:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "trigger_event must be one of: "
                         + ", ".join(sorted(TRIGGER_SUBJECTS)),
            }
        if not (message or recipient or trigger):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "there is nothing to notify about: send a message, "
                         "a recipient, or a trigger_event",
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    subject = subject or TRIGGER_SUBJECTS[trigger]
    # The record's own trigger_event IS the notification content when the
    # caller supplied no prose: the subject is the trigger's phrasing and
    # the body names the trigger and the reference. Nothing is claimed as
    # delivered on a channel that did not carry it -- an unconfigured
    # channel falls through to the in-process MCP ping below and the reply
    # says which channel carried it.
    body = message or f"{TRIGGER_SUBJECTS[trigger]} ({trigger})"
    envelope = {
        "channel": channel,
        "to": recipient,
        "subject": subject,
        "message": body,
        "payload": {"reference": reference, "trigger_event": trigger},
    }
    # A channel the operator has not configured (no SMTP, no webhook) is not a
    # failed notification: the ping still has to reach the broker, so it falls
    # back to the in-process MCP channel and the record says which channel was
    # used and why the requested one did not carry it. Nothing is claimed as
    # delivered on a channel that refused it.
    channel_fallback = ""
    # The requested channel is attempted as a PROBE: a channel the operator has
    # simply not configured is a fallback case, not a failed capability, and it
    # must not be recorded as a block failure before the fallback runs.
    requested = probe_block(
        "notification",
        envelope,
        action="send",
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    requested = requested["result"] if requested.get("ok") else {}
    if requested.get("sent") is not True and channel != "mcp":
        fallback = runner(
            "notification",
            {**envelope, "channel": "mcp", "block": "event_bus", "tool": "event_bus"},
            action="send",
        )
        channel_fallback = (
            f"{channel} did not carry it (not configured); delivered on mcp instead"
        )
        sent = fallback
        used_channel = "mcp"
    elif requested.get("sent") is True:
        sent = requested
        used_channel = str(sent.get("channel") or channel) if isinstance(sent, dict) else channel

    steps = [
        {
            "id": "step_0",
            "block": "event_bus",
            "action": "publish",
            "params": {"action": "publish"},
            "input": {
                "topic": f"notification.{trigger}",
                "payload": {"reference": reference, "trigger_event": trigger},
                "message": f"{subject}: {body}"[:400],
                "channel": "mcp",
                "tool": "event_bus",
            },
        }
    ]
    if not isinstance(sent, dict) or not sent:
        # Requested channel is mcp and it refused: that is a real block failure
        # and the capability reports it rather than queuing a silent nothing.
        sent = runner("notification", envelope, action="send")

    published = runner("event_bus", steps[0]["input"], action="publish")

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    delivered = bool(sent.get("sent")) if isinstance(sent, dict) else False
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "trigger_event": trigger,
        "subject": subject,
        "requested_channel": channel,
        "channel_used": used_channel,
        "delivered": delivered,
        "delivery_state": "sent" if delivered else "queued",
        "recipient": recipient,
        "channel_fallback": channel_fallback,
        "event": {
            "topic": published.get("topic") if isinstance(published, dict)
            else f"notification.{trigger}",
            "correlation_id": published.get("correlation_id")
            if isinstance(published, dict) else None,
        },
        "blocks": runner.report(),
    }
