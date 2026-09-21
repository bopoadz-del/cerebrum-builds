"""Local block dispatch. No network, no store, no callback.

The old generated platforms answered a capability by POSTing to the operator's
block store. This imports the block that was vendored into this repository at
build time and calls it in-process, which is what makes the platform runnable
offline and independent of the factory's uptime.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict

_VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "blocks"
_CACHE: Dict[str, Any] = {}


class BlockNotVendored(RuntimeError):
    """Asked for a block this platform does not carry."""


def load_block(block_id: str):
    """Resolve one vendored block: the CLONER adapter, then the Store class.

    ``vendor/blocks/<id>/block.py`` is the adapter the CLONER writes. Two of
    the blocks this product's bindings name cannot load through it in a
    delivered tree, because the adapter reaches for a Store runtime slice the
    delivery does not carry:

      document_engine  its package __init__ loads ``document_engine_block.py``
                       by path, and only the package directory ships
      knowledge        imports ``vendor.cerebrum.core.vector_store``, absent

    For those, the SAME Store class is loaded through the vendored registry
    (``vendor.cerebrum.blocks.get_block``) -- the block, not a re-implementation
    of it -- and wrapped in the adapter's own calling convention. When even the
    registry cannot import the module, ``run()`` refuses by name instead of
    raising an import error: the failure is "this delivery cannot run that
    block", and it says so.
    """
    if block_id in _CACHE:
        return _CACHE[block_id]
    path = _VENDOR / block_id / "block.py"
    if not path.is_file():
        raise BlockNotVendored(
            f"{block_id} is not vendored in this platform (looked in {path})"
        )
    spec = importlib.util.spec_from_file_location(f"vendored_{block_id}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, FileNotFoundError, ModuleNotFoundError) as exc:
        module = _registry_module(block_id, path, exc)
    else:
        module = _wrap_call_time_fallback(module, block_id, path)
    _CACHE[block_id] = module
    return module


def _wrap_call_time_fallback(module: Any, block_id: str, path: Path):
    """Adapters import their Store class lazily -- inside run()."""
    original = getattr(module, "run", None)
    if not callable(original):
        return module

    def run(**kwargs):
        try:
            return original(**kwargs)
        except (ImportError, FileNotFoundError, ModuleNotFoundError) as exc:
            return _registry_module(block_id, path, exc).run(**kwargs)

    return _ModuleShim(run=run, __file__=str(path), __name__=getattr(module, "__name__", ""))


class _ModuleShim:
    """The adapter's run() with the registry fallback behind it."""

    def __init__(self, run, __file__, __name__):
        self.run = run
        self.__file__ = __file__
        self.__name__ = __name__


def _registry_module(block_id: str, path: Path, adapter_exc: BaseException):
    """Wrap the registry-verified Store class, or a refusing stand-in.

    The Store class is looked up the way the delivery documents it, in order:

    1. the wrapper module the CLONER's shim names (``<block_id>_block``) --
       imported directly, because the block's package ``__init__`` loads that
       same file by path and that path is what is missing;
    2. the vendored registry (``vendor.cerebrum.blocks.get_block``).
    """
    import sys

    for stale_key in (
        f"vendor.cerebrum.blocks.{block_id}_block",
        f"vendor.cerebrum.blocks.{block_id}",
    ):
        # A failed load leaves an EMPTY module cached under that name: the
        # package __init__ registers it in sys.modules *before* executing it,
        # and Python only cleans up the module it was importing. Drop the stale
        # entry, then import for real.
        stale = sys.modules.get(stale_key)
        if stale is not None and not [
            name for name in dir(stale) if not name.startswith("__")
        ]:
            sys.modules.pop(stale_key, None)

    block_cls = None
    last_exc: BaseException = RuntimeError("registry not consulted")
    try:
        wrapper = importlib.import_module(f"vendor.cerebrum.blocks.{block_id}_block")
        for name in dir(wrapper):
            candidate = getattr(wrapper, name, None)
            if isinstance(candidate, type) and name.endswith("Block"):
                block_cls = candidate
                break
        if block_cls is None:
            last_exc = RuntimeError(f"{block_id}_block exposes no Block class")
    except Exception as exc:  # noqa: BLE001 - fall through to the registry
        last_exc = exc
    if block_cls is None:
        try:
            from vendor.cerebrum.blocks import get_block

            block_cls = get_block(block_id)
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            last_exc = exc
    if block_cls is None:
        reason = (
            f"{block_id} is not loadable in this delivery: adapter "
            f"{type(adapter_exc).__name__} ({adapter_exc}); store class "
            f"{type(last_exc).__name__} ({last_exc})"
        )

        def _refuse(**_kwargs):
            raise RuntimeError(reason)

        return _ModuleShim(run=_refuse, __file__=str(path), __name__=f"vendored_{block_id}")

    def _run(**kwargs):
        input_data = kwargs.get("input", kwargs)
        params = {key: value for key, value in kwargs.items() if key != "input"}
        instance = _instantiate_registry_class(block_cls)
        envelope = _run_async(instance.execute(input_data, params))
        if isinstance(envelope, dict):
            if str(envelope.get("status") or "").lower() in ("error", "failed"):
                inner = envelope.get("result")
                message = inner.get("error") if isinstance(inner, dict) else str(inner)
                raise RuntimeError(message or f"{block_id} block failed")
            return envelope.get("result", envelope)
        return envelope

    return _ModuleShim(run=_run, __file__=str(path), __name__=f"vendored_{block_id}")


def _instantiate_registry_class(block_cls):
    """Store classes take (hal_block, config); kit shims take nothing."""
    attempts = []
    for call in (
        lambda: block_cls(_offline_hal(), {}),
        lambda: block_cls(None, {}),
        lambda: block_cls(),
    ):
        try:
            return call()
        except TypeError as exc:
            attempts.append(exc)
    raise attempts[-1]


class _DispatchHal:
    """In-process HAL so a Store DatabaseBlock can open its SQLite file."""

    def __init__(self, db_path):
        self._db_path = db_path
        self._conn = None
        self.config = {}

    def _connect(self):
        if self._conn is None:
            import sqlite3

            parent = Path(self._db_path).parent
            parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @property
    def connection(self):
        return self._connect()

    def get_connection(self):
        return self._connect()

    def cursor(self):
        return self._connect().cursor()

    def execute(self, *args, **kwargs):
        return self._connect().execute(*args, **kwargs)

    def commit(self):
        self._connect().commit()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _offline_hal():
    import os

    root = Path(os.environ.get("STORAGE_PATH") or ".").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return _DispatchHal(str(root / "store_blocks.sqlite"))


def _run_async(coro):
    """Run a coroutine from sync code, inside or outside a loop."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()



#: Blocks whose own input schema declares the operation as a payload field
#: (harvested: the block reads ``.get("action")`` off the record it is handed
#: and declares no JSON ``input`` slot). For these the operation travels in the
#: payload as well as the keyword; for every other block the keyword alone is
#: the contract, and an ``action`` key inside the payload is a defect.
_PAYLOAD_ACTION_BLOCKS = {'guest_rfm_segmentation', 'estate_maintenance', 'estate_registry', 'hospitality_connectors', 'multi_tenant_rbac', 'channel_router'}

BLOCK_CONTRACTS: Dict[str, Any] = {'billing': {'action_options': ['record_usage', 'check_quota', 'check_purchase', 'record_purchase', 'create_customer', 'create_subscription', 'get_invoice', 'upgrade', 'webhook'], 'block_id': 'billing', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'json'}, {'name': 'stripe_key', 'required': False, 'type': 'string'}, {'name': 'free_tier_requests', 'required': False, 'type': 'number'}, {'name': 'pro_tier_requests', 'required': False, 'type': 'number'}], 'default_action': 'record_usage', 'input_keys_read_by_block': ['action', 'api_key', 'block', 'block_id', 'customer_id', 'email', 'hit', 'name', 'payload', 'plan', 'purchased', 'requests', 'role', 'signature', 'stripe_price_id', 'stripe_secret_key', 'stripe_subscription_item', 'stripe_webhook_secret', 'tokens', 'user_id', 'valid', 'value'], 'payload_action': False, 'runtime_error_contracts': ['Stripe not configured', 'Unknown action', 'Webhook handling not configured', 'api_key/user_id and block_id required']}, 'channel_router': {'block_id': 'channel_router', 'input_keys_read_by_block': ['account', 'action', 'advice_needed', 'affinity_referral', 'agency_relationship', 'annual_premium', 'channel_constraints', 'complexity', 'customer', 'digital_preference', 'fast_quote_needed', 'hard_to_place', 'line_of_business', 'lob', 'needs_advice', 'operation', 'partner_referral', 'premium', 'product', 'relationship_strength', 'risk_complexity', 'self_service_preference', 'specialty_risk', 'speed_priority', 'submission'], 'payload_action': True}, 'dashboard': {'action_options': ['render', 'add_widget', 'remove_widget', 'update_widget', 'get_metrics', 'list_widgets', 'save_layout', 'get_layout', 'subscribe_stream', 'get_snapshot'], 'block_id': 'dashboard', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'json'}, {'name': 'default_layout', 'required': False, 'type': 'string'}, {'name': 'refresh_interval', 'required': False, 'type': 'number'}, {'name': 'max_widgets', 'required': False, 'type': 'number'}, {'name': 'theme', 'required': False, 'type': 'string'}], 'default_action': 'render', 'input_keys_read_by_block': ['action', 'callback', 'config', 'data_source', 'default_layout', 'hit', 'layout', 'max_widgets', 'position', 'refresh_interval', 'theme', 'title', 'type', 'updates', 'user_id', 'value', 'widget_id', 'widgets'], 'payload_action': False, 'runtime_error_contracts': ['Maximum widgets reached', 'Widget not found']}, 'document_engine': {'block_id': 'document_engine', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'string'}, {'name': 'extract_tables', 'required': False, 'type': 'boolean'}, {'name': 'extract_glossary', 'required': False, 'type': 'boolean'}, {'name': 'output_format', 'required': False, 'type': 'string'}, {'name': 'use_platform_pdf', 'required': False, 'type': 'boolean'}, {'name': 'use_platform_ocr', 'required': False, 'type': 'boolean'}], 'payload_action': False, 'input_keys_read_by_block': ['brief', 'bytes', 'document_engine', 'docx', 'docx_path', 'file_path', 'input', 'path', 'pdf', 'pdf_path', 'status', 'text', 'use_platform_ocr', 'use_platform_pdf', 'xlsx', 'xlsx_path']}, 'estate_maintenance': {'action_options': ['create', 'list', 'complete'], 'block_id': 'estate_maintenance', 'declared_inputs': [{'name': 'title', 'required': True, 'type': 'string'}, {'name': 'due', 'required': False, 'type': 'string'}, {'name': 'id', 'required': False, 'type': 'string'}], 'default_action': 'create', 'input_keys_read_by_block': ['action', 'created_at', 'due', 'id', 'status', 'title'], 'payload_action': True}, 'estate_registry': {'action_options': ['create', 'read', 'list'], 'block_id': 'estate_registry', 'declared_inputs': [{'name': 'id', 'required': True, 'type': 'string'}, {'name': 'data', 'required': False, 'type': 'json'}], 'default_action': 'create', 'input_keys_read_by_block': ['action', 'id', 'record', 'records', 'store_dir'], 'payload_action': True}, 'guest_rfm_segmentation': {'action_options': ['score', 'batch'], 'block_id': 'guest_rfm_segmentation', 'input_keys_read_by_block': ['action', 'f_thresholds', 'frequency', 'guest_id', 'guests', 'id', 'm_thresholds', 'monetary', 'r_thresholds', 'recency_days'], 'payload_action': True}, 'hospitality_connectors': {'action_options': ['ingest', 'fetch', 'connect', 'normalise', 'bus', 'systems'], 'block_id': 'hospitality_connectors', 'input_keys_read_by_block': ['action', 'amount', 'arrival', 'asset_id', 'asset_type', 'check_id', 'closed', 'comp_balance', 'confirmation_id', 'controller_id', 'covers', 'departure', 'dnd', 'evidence_class', 'grms_cert_matches_config', 'guest_id', 'hk_status', 'host', 'id', 'limit', 'linked_reservation', 'location', 'market', 'nights', 'occupied', 'outlet', 'player_id', 'points', 'profile_id', 'rate_code', 'raw', 'records', 'resource', 'room', 'room_map_complete', 'room_type', 'rooms', 'serial_number', 'source_system', 'status', 'statutory_flag', 'surface', 'system', 'tier', 'topic_prefix', 'vip', 'wo'], 'payload_action': True}, 'hotel_v2': {'block_id': 'hotel_v2', 'declared_inputs': [{'name': 'text', 'required': False, 'type': 'string'}], 'input_keys_read_by_block': ['analysis_type', 'cancellations', 'custom_rules', 'document_type', 'gross_profit', 'include_raw', 'no_shows', 'room_revenue', 'rooms_sold', 'rules', 'total_arrivals', 'total_bookings', 'total_revenue', 'total_rooms', 'value', 'walk_ins'], 'payload_action': False, 'runtime_error_contracts': ['Missing arrival or departure date', 'Missing cancellations or total bookings', 'Missing gross profit or total rooms', 'Missing no-shows or total bookings', 'Missing revenue or rooms sold', 'Missing revenue or total rooms', 'Missing rooms sold or total rooms', 'Missing walk-ins or total arrivals']}, 'knowledge': {'action_options': ['ask', 'search', 'summarize'], 'block_id': 'knowledge', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'string'}, {'name': 'top_k', 'required': False, 'type': 'number'}, {'name': 'llm_provider', 'required': False, 'type': 'string'}, {'name': 'ollama_base_url', 'required': False, 'type': 'string'}, {'name': 'ollama_model', 'required': False, 'type': 'string'}, {'name': 'deepseek_api_key', 'required': False, 'type': 'string'}, {'name': 'deepseek_model', 'required': False, 'type': 'string'}, {'name': 'openrouter_api_key', 'required': False, 'type': 'string'}, {'name': 'openrouter_model', 'required': False, 'type': 'string'}, {'name': 'vector_db_url', 'required': False, 'type': 'string'}, {'name': 'default_top_k', 'required': False, 'type': 'number'}, {'name': 'default_collections', 'required': False, 'type': 'array'}], 'default_action': 'ask', 'input_keys_read_by_block': ['action', 'chunk_id', 'collection', 'collections', 'content', 'corpus_total', 'default_collections', 'default_top_k', 'document', 'document_id', 'documents_indexed', 'error', 'id', 'input', 'llm_provider', 'metadata', 'n_docs', 'project_id', 'query', 'question', 'result', 'results', 'score', 'status', 'text', 'top_k', 'vector_db_url'], 'payload_action': False, 'runtime_error_contracts': ['Kimi API key not configured (set KIMI_API_KEY)']}, 'mcp_adapter': {'action_options': ['list_tools', 'describe'], 'block_id': 'mcp_adapter', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'json'}, {'name': 'tool', 'required': False, 'type': 'string'}], 'default_action': 'list_tools', 'input_keys_read_by_block': ['action', 'tool'], 'payload_action': False}, 'multi_tenant_rbac': {'block_id': 'multi_tenant_rbac', 'input_keys_read_by_block': ['action', 'mode', 'name', 'needed', 'owner_id', 'permissions', 'project_id', 'role', 'tenant_id', 'user_id'], 'payload_action': True, 'runtime_error_contracts': ['Unknown action: %s', 'permission denied', 'project_id required', 'tenant exists', 'tenant_access_denied', 'tenant_id and owner_id required', 'unknown tenant or user']}, 'notification': {'action_options': ['send', 'broadcast', 'health'], 'block_id': 'notification', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'json'}, {'name': 'sendgrid_api_key', 'required': False, 'type': 'string'}, {'name': 'smtp_host', 'required': False, 'type': 'string'}, {'name': 'smtp_port', 'required': False, 'type': 'number'}, {'name': 'smtp_user', 'required': False, 'type': 'string'}, {'name': 'smtp_pass', 'required': False, 'type': 'string'}, {'name': 'slack_webhook_url', 'required': False, 'type': 'string'}, {'name': 'default_from_email', 'required': False, 'type': 'string'}], 'default_action': 'send', 'input_keys_read_by_block': ['action', 'block', 'blocks', 'body', 'channel', 'channels', 'default_from_email', 'email', 'event', 'from', 'headers', 'html', 'input', 'limit', 'message', 'method', 'params', 'payload', 'sendgrid_api_key', 'slack_webhook_url', 'smtp_host', 'smtp_pass', 'smtp_port', 'smtp_retry_backoff', 'smtp_timeout', 'smtp_user', 'source', 'status', 'subject', 'text', 'to', 'tool', 'url', 'webhook_retry_backoff', 'webhook_timeout', 'webhook_url'], 'input_required_fields': ['channel', 'message'], 'payload_action': False, 'runtime_error_contracts': ['Block ', 'SMTP not configured (set SMTP_HOST or SENDGRID_API_KEY)', 'SMTP_URL must be smtp://, smtps:// or smtp+starttls:// with a host', 'Slack webhook URL not configured', 'aiosmtplib not installed. Run: pip install aiosmtplib', 'block or tool name required for MCP channel', 'channel required: one of mcp | email | webhook | smtp | slack', 'channels required: any of mcp | email | webhook | smtp | slack', 'to (email) required', 'to (email) required, or set NOTIFY_SMTP_TO']}, 'workflow': {'action_options': ['run', 'schedule', 'unschedule', 'list', 'get', 'history', 'status', 'health'], 'block_id': 'workflow', 'declared_inputs': [{'name': 'input', 'required': False, 'type': 'json'}, {'name': 'max_pipeline_steps', 'required': False, 'type': 'number'}, {'name': 'enable_scheduler', 'required': False, 'type': 'boolean'}, {'name': 'default_timeout', 'required': False, 'type': 'number'}], 'default_action': 'run', 'input_keys_read_by_block': ['STORAGE_PATH', 'action', 'block', 'block_id', 'break_on_error', 'cron', 'default_timeout', 'enable_scheduler', 'id', 'input', 'interval_seconds', 'max_pipeline_steps', 'params', 'pipeline_id', 'properties', 'result', 'status', 'steps', 'stop_on_error', 'timeout', 'trigger'], 'input_required_fields': ['steps'], 'payload_action': False, 'runtime_error_contracts': ['Block ', 'Chain validation failed — incompatible blocks', 'No block specified', 'No steps defined', 'Pipeline ', 'Schedule requires cron or interval_seconds', 'Scheduler disabled', 'pipeline_id required for scheduling']}}


class DispatchContractError(ValueError):
    """Caller payload failed the harvested contract. Do not invent fields."""


#: Every envelope this dispatcher had to normalise, as
#: ``(block_id, lifted_keys)``. A silent normalisation is still a defect in
#: the generated handler; the WRITER contract probe reads this list so the
#: mismatch is NAMED rather than absorbed.
_LIFTED: list = []


def _required_fields(block_id: str) -> list:
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    required = list(contract.get("input_required_fields") or [])
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name and item.get("required") and name not in required:
            required.append(name)
    return [field for field in required if field != "action"]


def _known_fields(block_id: str) -> set:
    """Closed field set from the harvested contract. Empty = no allow-list.

    Three sources, and the third is the one that was missing:

    * ``declared_inputs`` -- the block's CONFIG parameters, from block.json
      (backend, connection_string, theme, ...).
    * ``input_required_fields`` -- what the block refuses to run without.
    * ``input_keys_read_by_block`` -- the keys the block's own code actually
      reads off its payload at run time (table, values, where, file_path,
      user_id, ...). WORKAROUND, harvested from source; see
      CerebrumDev.ai#256 and Cerebrum-Blocks#90.

    Leaving the third one out is what made every generated platform inert.
    ``database`` declares only {input, backend, connection_string}, so a
    correct call -- ``{"table": "crew_logs", "values": {...}}`` -- had both
    keys counted as stray, folded into ``input`` by _adapt_input below, and
    handed to the block double-wrapped. ``_insert`` then read ``table=None``
    and ``values={}`` and emitted ``INSERT INTO None () VALUES ()``:

        database: Insert failed: near ")": syntax error

    One defect, four faces, measured on the booted zip of session
    sess_6400b6c: ``document_engine`` answered "No input files provided"
    holding a file_path, ``notification`` answered "block or tool name
    required for MCP channel" holding a block name, and ``team`` answered
    "Team access denied" holding a user_id. The platform built, shipped,
    booted and served all seventeen routes -- and could not persist a row.

    The fold itself stays: a key the block never reads is still a domain
    record and still belongs in ``input`` (the warehouse `audit` case the
    fold was written for). Only keys the block reads stay flat.
    """
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    names: set = set()
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name and name != "action":
            names.add(name)
    for field in contract.get("input_required_fields") or []:
        if field != "action":
            names.add(field)
    for field in contract.get("input_keys_read_by_block") or []:
        if field and field != "action":
            names.add(str(field))
    return names


def _keys_read(block_id: str) -> set:
    """Only the keys the block's CODE reads off its payload at run time.

    Distinct from ``_known_fields``, which also carries block.json's declared
    CONFIG params. The distinction is what tells a declared ``input`` slot
    from one the block actually reads: measured on the vendored blocks,
    ``analytics``, ``database``, ``team`` and ``storage`` contain ZERO
    ``.get("input")`` -- they read their keys flat -- while ``workflow``
    reads one. Both facts are needed below.

    WORKAROUND: ``input_keys_read_by_block`` is regex-harvested from the
    vendored source because no manifest declares it yet. When block.json
    carries ``requires_inputs`` (Cerebrum-Blocks#90), that declaration
    replaces this read -- removal tracked in CerebrumDev.ai#256.
    """
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    return {
        str(f) for f in (contract.get("input_keys_read_by_block") or []) if f
    }


def _envelope_mismatch(block_id: str, data: Dict[str, Any]) -> tuple:
    """Is the caller's record one level too deep for this block?

    Returns ``(buried, colliding)`` -- the keys the block reads that sit
    inside ``data["input"]`` instead of at the top level, and any of those
    that already exist at the top level with a different value.

    THE INCIDENT (residential-lettings, sess_6400b6c273414352, post-#254).
    ``unit_registry_and_vacancy_tracking`` called::

        execute("analytics", {"input": {"metric": "monthly_rent_gbp",
                                        "value": 1450.0, ...}},
                action="track_event")

    and got ``{'error': 'metric and value required'}``. Verified literally in
    the block source: ``AnalyticsBlock._track_event`` reads
    ``data.get("metric")`` and ``data.get("value")`` off the payload it is
    handed, and ``analytics``' block.json declares ``input`` only as a config
    slot -- the code never reads it. Both fields were present in the spec, so
    a plan-time audit that looks for NAMES passes; the block still saw
    neither. That is #254's class one level deeper, and the same file wrapped
    three different shapes with no rule.
    """
    reads = _keys_read(block_id)
    if not reads or "input" in reads:
        # The block genuinely reads an ``input`` key (``workflow`` does).
        # Its wrapper is the contract, not a mistake.
        return (), ()
    inner = data.get("input")
    if not isinstance(inner, dict):
        return (), ()
    buried = sorted(k for k in inner if k in reads and k != "action")
    colliding = sorted(
        k for k in buried if k in data and data[k] != inner[k]
    )
    return tuple(buried), tuple(colliding)


def _adapt_input(block_id: str, payload: Any, action: str | None) -> Dict[str, Any]:
    """Pass the caller payload through. Never invent Store fields (F18).

    A MISMATCHED ENVELOPE IS NEVER PASSED THROUGH SILENTLY. Either the
    record is normalised to the shape the block reads, or the call fails
    with the mismatch named -- it does not reach the block wearing a shape
    the block cannot read (owner's ruling R1d, 2026-09-01).
    """
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    known = _known_fields(block_id)

    buried, colliding = _envelope_mismatch(block_id, data)
    if colliding:
        # Two different values for the same field, one nested and one flat.
        # Normalising would have to choose, and choosing is inventing.
        verb = "appears" if len(colliding) == 1 else "appear"
        raise DispatchContractError(
            f"{block_id} envelope mismatch: {', '.join(colliding)} {verb} both "
            f"at the top level and inside 'input' with different values; "
            f"{block_id} reads them at the top level. Pass the record flat."
        )
    if buried:
        inner = dict(data.get("input") or {})
        for key in buried:
            data[key] = inner.pop(key)
        if inner:
            data["input"] = inner
        else:
            data.pop("input", None)
        _LIFTED.append((block_id, tuple(buried)))
    # Store blocks are action-dispatched: the domain record travels in the
    # block's declared ``input`` slot, with block params beside it. A handler
    # that passes the record flat gets every domain key refused as unknown --
    # measured on the warehouse `audit` capability, which declares
    # reference/status/quantity in its own model and had all three rejected.
    #
    # This is adaptation, not F18 fabrication. No value is invented and no
    # field is conjured to satisfy a validator: the caller's own record is
    # placed in the field the block declares for exactly it. If the caller
    # already supplied ``input``, nothing is moved.
    if known and "input" in known and "input" not in data:
        stray = {k: v for k, v in data.items() if k not in known}
        if stray:
            data = {k: v for k, v in data.items() if k in known}
            data["input"] = stray
    missing = [
        field for field in _required_fields(block_id)
        if field not in data or data[field] in (None, "")
    ]
    if missing:
        raise DispatchContractError(
            f"{block_id} missing required field(s): {', '.join(missing)}"
        )
    if known:
        allowed = set()
        if block_id in _PAYLOAD_ACTION_BLOCKS:
            # The block's own input schema declares the operation as a field
            # (estate_registry, estate_maintenance, hospitality_connectors and
            # friends read ``payload["action"]`` and ignore the params the
            # adapter hands them). The operation travels BOTH in the payload --
            # the only place those blocks look -- and as the action= keyword.
            allowed.add("action")
        unknown = sorted(str(key) for key in data if key not in known and key not in allowed)
        if unknown:
            raise DispatchContractError(
                f"{block_id} unknown field(s): {', '.join(unknown)}"
            )
    return data


#: A block that answers with one of these has NOT succeeded. "partial" is the
#: word both the workflow and notification blocks use for "some of it failed"
#: -- workflow sets it on every step that raises, times out, names an unknown
#: block, or returns an error. Reading only "error" let a pipeline whose only
#: step failed come back as success.
_FAILED_STATUSES = {"error", "failed", "partial"}


def _failed_steps(result: Dict[str, Any]) -> list:
    """Sub-step failures the top-level status may not carry.

    Live, from the booted sess_6400b6c zip: punch_list_tracking returned
    ``ok: true`` wrapped around

        {"status": "partial", "results": [{"step_id": "step_0",
          "block": "database", "status": "failed",
          "error": "DatabaseBlock.__init__() missing 2 required positional
          arguments: 'hal_block' and 'config'"}]}

    The capability reported success. The row was never written.
    """
    steps = result.get("results")
    if not isinstance(steps, list):
        steps = result.get("steps")
    if not isinstance(steps, list):
        return []
    return [
        step for step in steps
        if isinstance(step, dict)
        and str(step.get("status") or "").lower() in {"error", "failed"}
    ]


def _error_envelope(block_id: str, action: str | None, error: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "block": block_id,
        "action": action,
        "error": error,
        "ok": False,
    }


def _force_utf8_stdio() -> None:
    """F13: a checkmark/emoji print must not become a charmap crash.

    Windows cp1252 consoles encode print() with the console codepage. A
    vendored block that prints one checkmark used to raise UnicodeEncodeError;
    execute() then swallowed that into a generic error envelope that looked
    like a domain refusal. Force UTF-8 on this process before the block runs.
    """
    import os
    import sys

    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            continue


_force_utf8_stdio()


def execute(
    block_id: str,
    payload: Dict[str, Any],
    action: str | None = None,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run a vendored block locally and return its result envelope.

    Real Store blocks are action-dispatched: the domain data travels as
    ``input`` and the operation name as ``action`` (each block declares a
    default in its block.json). A call with no action reaches blocks that
    answer "Unknown action" -- pass the one the capability needs.

    Missing required fields and unknown fields/params become an error
    envelope. A block refusal (status=error) is returned as-is — never
    rewritten to ok.
    """
    module = load_block(block_id)
    run = getattr(module, "run", None)
    if run is None:
        raise BlockNotVendored(f"{block_id} exposes no run() entry point")
    contract = BLOCK_CONTRACTS.get(block_id) or {}
    declared = set()
    for item in contract.get("declared_inputs") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if name:
            declared.add(name)
    if (
        params
        and (contract.get("declared_inputs") or contract.get("input_required_fields"))
    ):
        extra = sorted(
            str(key) for key in params if key not in declared and key != "action"
        )
        if extra:
            return _error_envelope(
                block_id, action, f"unknown param(s): {', '.join(extra)}"
            )
    kwargs = dict(params or {})
    if action is not None:
        kwargs["action"] = action
    try:
        adapted = _adapt_input(block_id, payload, action)
    except DispatchContractError as exc:
        return _error_envelope(block_id, action, str(exc))
    # A block-level failure comes back as data, not as an exception. The
    # Store's shim raises RuntimeError on an error envelope, which destroys
    # the diagnosis: a handler (and a failing test) sees "Input validation
    # failed" with no block name and no field list. Structural failures --
    # a block that is not vendored -- still raise above.
    _force_utf8_stdio()
    try:
        result = run(input=adapted, **kwargs)
    except BlockNotVendored:
        raise
    except UnicodeEncodeError as exc:
        return _error_envelope(
            block_id,
            action,
            f"UnicodeEncodeError on block stdout (encoding, not domain): {exc}",
        )
    except Exception as exc:
        return _error_envelope(
            block_id, action, f"{type(exc).__name__}: {exc}"
        )
    if isinstance(result, dict):
        status = str(result.get("status") or "").lower()
        failed = _failed_steps(result)
        if status in _FAILED_STATUSES or result.get("ok") is False or failed:
            refused = dict(result)
            refused["status"] = status if status in _FAILED_STATUSES else "error"
            refused.setdefault("block", block_id)
            refused["ok"] = False
            if failed and not refused.get("error"):
                refused["error"] = "; ".join(
                    "%s (%s): %s" % (
                        step.get("step_id") or "step",
                        step.get("block") or "?",
                        str(step.get("error") or step.get("status"))[:160],
                    )
                    for step in failed
                )
            return refused
    return result
