#!/usr/bin/env python3
"""Store-green acceptance — ≥12 measured checks. Presence-only is a fail.

Authorship floor is the LAST line. HTTP 200 ok:false is not a pass.
RAG skip policy: SKIP:no-rag-surface only when the product has no RAG
route or rag capability. Steward must plant + hit.

Measurement provenance (honesty rule for this file):

* ``docker_health_200`` and ``postgres_boot_200`` are measurements only the
  gate host can take -- it owns the container probe and the Postgres boot.
  This script reports what the host measured and FAILS LOUD when the host
  measured nothing. It never fabricates either number.
* ``bench_p95``, ``backup_restore_roundtrip`` and ``one_live_connector`` are
  measurements this script CAN take from inside the image, so it takes them
  when the host did not: it runs ``scripts/bench.py``, it performs a real
  backup → wipe → restore drill against a scratch STORAGE_PATH with rows
  asserted on both sides, and it drives ``app.notify.deliver`` down a real
  SMTP socket to a local sink and asserts the message arrived. A host that
  supplies ``STORE_BENCH_P95_MS`` / ``STORE_BACKUP_RESTORE`` /
  ``STORE_LIVE_CONNECTOR`` still wins -- but an unset variable now means
  "this script measured it", not "nobody looked".
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ['no_token_401', 'missing_field_422', 'enum_422', 'ui_served_200', 'rag_roundtrip_hit', 'single_persistence_root', 'ci_present_and_full_suite', 'handler_bodies_distinct', 'health_fail_closed', 'openapi_committed', 'docker_health_200', 'cross_tenant_404', 'migration_no_create_all', 'negative_floor', 'postgres_boot_200', 'one_live_connector', 'metrics_served', 'backup_restore_roundtrip', 'bench_p95', 'audit_clean', 'authorship_floor']
REQUIRED = 21


def _token() -> str:
    return (os.environ.get("PLATFORM_TOKEN") or "dev-local-token").strip()


def _auth() -> Dict[str, str]:
    return {"Authorization": "Bearer " + _token()}


class _Http:
    def __init__(self, client: Any):
        self.client = client

    def request(self, method: str, path: str, **kw: Any) -> Any:
        fn = getattr(self.client, method.lower())
        return fn(path, **kw)


def _client() -> Tuple[_Http, Any]:
    base = (os.environ.get("ACCEPTANCE_BASE_URL") or "").rstrip("/")
    if base:
        import urllib.error
        import urllib.request

        class _Url:
            def request(self, method: str, path: str, json=None, headers=None, **_kw):
                data = None
                hdrs = dict(headers or {})
                if json is not None:
                    data = json_mod.dumps(json).encode("utf-8")
                    hdrs.setdefault("Content-Type", "application/json")
                req = urllib.request.Request(base + path, data=data, headers=hdrs, method=method.upper())
                try:
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        body = resp.read()
                        return _Resp(resp.status, body, resp.headers)
                except urllib.error.HTTPError as exc:
                    return _Resp(exc.code, exc.read(), exc.headers)

        import json as json_mod

        class _Resp:
            def __init__(self, status, body, headers):
                self.status_code = int(status)
                self._body = body or b""
                self.headers = headers or {}
                self.content = self._body

            def json(self):
                return json.loads(self._body.decode("utf-8") or "{}")

            @property
            def text(self) -> str:
                return self._body.decode("utf-8", errors="replace")

        url = _Url()

        class _Wrap:
            def get(self, path, **kw):
                return url.request("GET", path, **kw)

            def post(self, path, **kw):
                return url.request("POST", path, **kw)

        return _Http(_Wrap()), None

    from fastapi.testclient import TestClient
    from app.main import app

    cm = TestClient(app)
    client = cm.__enter__()
    return _Http(client), cm


def _first_cap() -> str:
    receipt = ROOT / "docs" / "coder_receipt.json"
    if receipt.is_file():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        caps = data.get("capabilities") or []
        if caps:
            first = caps[0]
            if isinstance(first, dict):
                return str(first.get("id") or first.get("capability_id") or "")
            return str(first)
    try:
        from app.jobs import CAPABILITIES

        for item in CAPABILITIES or []:
            if isinstance(item, dict) and item.get("id"):
                return str(item["id"])
            if isinstance(item, str) and item.strip():
                return item
    except Exception:
        pass
    try:
        from app.models import MODELS

        if MODELS:
            return sorted(MODELS)[0]
    except Exception:
        pass
    return ""


def _models():
    try:
        from app.models import MODELS

        return MODELS
    except Exception:
        return {}


def _required_and_enum(cap_id: str) -> Tuple[Optional[str], Optional[Tuple[str, List[Any]]]]:
    models = _models()
    cls = models.get(cap_id) if cap_id else None
    required = None
    enum = None
    if cls is not None:
        fields = list(getattr(cls, "FIELDS", []) or [])
        constraints = getattr(cls, "CONSTRAINTS", {}) or {}
        for name in fields:
            rules = constraints.get(name) or {}
            if rules.get("required") and required is None:
                required = name
            allowed = rules.get("allowed_values") or []
            if allowed and enum is None:
                enum = (name, list(allowed))
    if required is None or enum is None:
        for other_id, other in models.items():
            fields = list(getattr(other, "FIELDS", []) or [])
            constraints = getattr(other, "CONSTRAINTS", {}) or {}
            for name in fields:
                rules = constraints.get(name) or {}
                if required is None and rules.get("required"):
                    required = name
                    cap_id = other_id
                if enum is None:
                    allowed = rules.get("allowed_values") or []
                    if allowed:
                        enum = (name, list(allowed))
    return required, enum


def _has_rag_surface() -> bool:
    for rel in (
        ROOT / "docs" / "rag" / "dual_rag.json",
        ROOT / "docs" / "coder_receipt.json",
    ):
        if not rel.is_file():
            continue
        try:
            blob = rel.read_text(encoding="utf-8").lower()
        except OSError:
            continue
        if "rag" in blob:
            return True
    try:
        from app.models import MODELS

        if any("rag" in str(k).lower() for k in MODELS):
            return True
    except Exception:
        pass
    try:
        from app.jobs import CAPABILITIES

        for item in CAPABILITIES or []:
            ident = item.get("id") if isinstance(item, dict) else item
            if "rag" in str(ident).lower():
                return True
    except Exception:
        pass
    main = ROOT / "app" / "main.py"
    routes = ROOT / "app" / "routes.py"
    text = ""
    for path in (main, routes):
        if path.is_file():
            text += path.read_text(encoding="utf-8")
    return bool(re.search(r"/v1/(steward/)?rag|/v1/dual_rag", text))


def check_no_token_401(http: _Http) -> Tuple[str, str]:
    cap = _first_cap()
    if not cap:
        return "FAIL", "no first capability to POST"
    resp = http.request("post", "/v1/" + cap, json={})
    if resp.status_code == 401:
        return "PASS", "HTTP 401"
    if resp.status_code == 200:
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        return "FAIL", "HTTP 200 ok:%s (must be 401, not ok:false)" % body.get("ok")
    return "FAIL", "HTTP %s (want 401)" % resp.status_code


def check_missing_field_422(http: _Http) -> Tuple[str, str]:
    cap = _first_cap()
    required, _enum = _required_and_enum(cap)
    if not cap:
        return "FAIL", "no capability"
    if not required:
        return "FAIL", "no required field to measure (not a presence skip)"
    resp = http.request("post", "/v1/" + cap, json={}, headers=_auth())
    if resp.status_code == 422:
        return "PASS", "HTTP 422 missing %s" % required
    return "FAIL", "HTTP %s (want 422 for missing %s)" % (resp.status_code, required)


def check_enum_422(http: _Http) -> Tuple[str, str]:
    cap = _first_cap()
    required, enum = _required_and_enum(cap)
    if not enum:
        return "FAIL", "no enum field to measure (not a presence skip)"
    name, allowed = enum
    payload: Dict[str, Any] = {}
    models = _models()
    cls = models.get(cap)
    if cls is not None:
        constraints = getattr(cls, "CONSTRAINTS", {}) or {}
        for field in getattr(cls, "FIELDS", []) or []:
            rules = constraints.get(field) or {}
            if rules.get("allowed_values"):
                payload[field] = rules["allowed_values"][0]
            elif rules.get("required"):
                payload[field] = "sample"
    payload[name] = "__not_in_contract__"
    resp = http.request("post", "/v1/" + cap, json=payload, headers=_auth())
    if resp.status_code == 422:
        return "PASS", "HTTP 422 invalid %s" % name
    return "FAIL", "HTTP %s (want 422 for invalid enum %s)" % (resp.status_code, name)


def check_ui_served_200(http: _Http) -> Tuple[str, str]:
    resp = http.request("get", "/")
    if resp.status_code != 200:
        return "FAIL", "GET / HTTP %s" % resp.status_code
    text = getattr(resp, "text", "") or ""
    ctype = ""
    headers = getattr(resp, "headers", {}) or {}
    if hasattr(headers, "get"):
        ctype = str(headers.get("content-type") or headers.get("Content-Type") or "")
    if "html" in ctype.lower() or "<html" in text.lower() or "<!doctype" in text.lower():
        return "PASS", "GET / HTTP 200 HTML"
    return "FAIL", "GET / was 200 but not served UI (content-type=%s)" % ctype


def _declared_v1_paths(match) -> List[str]:
    """POST-able /v1 paths the PRODUCT declares, filtered by ``match``.

    The plant/query paths used to be a hand-kept list, and four of the eight
    named one product's routes (/v1/steward/rag/*, /v1/dual_rag_estate_docs).
    Any product that calls its retrieval surface something else -- which is
    every product with a different brief -- failed with "plant did not
    accept" while having working retrieval. openapi.json is committed and
    current (the floor requires it), so the product declares its own routes
    and this reads them.
    """
    doc_path = ROOT / "docs" / "openapi.json"
    try:
        doc = json.loads(doc_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for path, ops in (doc.get("paths") or {}).items():
        name = str(path)
        if not name.startswith("/v1/"):
            continue
        if not isinstance(ops, dict) or "post" not in {k.lower() for k in ops}:
            continue
        if match(name.lower()):
            out.append(name)
    return out


def _rag_ingest_paths() -> List[str]:
    declared = _declared_v1_paths(
        lambda n: ("ingest" in n or "upload" in n or "index" in n or "add" in n)
        and ("rag" in n or "doc" in n or "knowledge" in n or "corpus" in n or "ingest" in n)
    )
    known = [
        "/v1/rag/ingest",
        "/v1/steward/rag/ingest",
        "/v1/dual_rag_sop",
        "/v1/dual_rag_estate_docs",
    ]
    return declared + [k for k in known if k not in declared]


def _rag_query_paths() -> List[str]:
    declared = _declared_v1_paths(
        lambda n: ("query" in n or "search" in n or "ask" in n or "retriev" in n)
        and ("rag" in n or "doc" in n or "knowledge" in n or "corpus" in n or "query" in n)
    )
    known = ["/v1/rag/query", "/v1/steward/rag/query", "/v1/rag/dual", "/v1/dual_rag_sop"]
    return declared + [k for k in known if k not in declared]


def check_rag_roundtrip_hit(http: _Http) -> Tuple[str, str]:
    if not _has_rag_surface():
        return "SKIP", "no-rag-surface"
    # The nonce identifies the planted content and MUST NEVER be sent as part
    # of the query request itself -- a prior version queried the exact phrase
    # it POSTed (and even resent the planted "text" in the query body), so any
    # endpoint that echoed its own request back (idiomatic REST design, not a
    # bug) satisfied this check regardless of whether retrieval ran at all.
    # A second, never-planted nonce is the negative control: a query for it
    # must come back EMPTY, or the "hit" mechanism is proven to be an echo.
    nonce = uuid.uuid4().hex[:12]
    absent_nonce = uuid.uuid4().hex[:12]
    marker = "ACCEPTANCE-PLANT-%s the reorder threshold procedure" % nonce
    ingest_paths = _rag_ingest_paths()
    planted = False
    for path in ingest_paths:
        resp = http.request(
            "post",
            path,
            json={"text": marker, "content": marker, "paragraph": marker},
            headers=_auth(),
        )
        if resp.status_code in (200, 201, 202):
            planted = True
            break
    if not planted:
        return "FAIL", "RAG surface present but plant did not accept"
    query_paths = _rag_query_paths()

    def _content_hit(resp: Any, needle: str) -> bool:
        # Only fields that are supposed to carry RETRIEVED content count --
        # never the raw response text (which can just be a request echo) and
        # never a field named "query"/"q" (which IS the request echoed back).
        if resp.status_code != 200:
            return False
        try:
            data = resp.json()
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        for key in ("hits", "results", "items", "matches", "chunks", "answer", "citations"):
            val = data.get(key)
            if val is None:
                continue
            if needle in json.dumps(val).lower():
                return True
        return False

    positive_hit = False
    negative_leak = False
    for path in query_paths:
        pos_resp = http.request(
            "post", path, json={"q": marker, "query": marker}, headers=_auth(),
        )
        if _content_hit(pos_resp, nonce.lower()):
            positive_hit = True
        neg_resp = http.request(
            "post", path, json={"q": absent_nonce, "query": absent_nonce}, headers=_auth(),
        )
        if _content_hit(neg_resp, absent_nonce.lower()):
            negative_leak = True
        if positive_hit or negative_leak:
            break
    if negative_leak:
        return "FAIL", "query for a never-planted term still came back as a hit (echo, not retrieval)"
    if positive_hit:
        return "PASS", "plant->retrieve round trip confirmed in a content field, not a request echo"
    return "FAIL", "RAG surface present but query missed"


def check_single_persistence_root() -> Tuple[str, str]:
    store = ROOT / "app" / "store.py"
    if not store.is_file():
        return "FAIL", "app/store.py missing"
    text = store.read_text(encoding="utf-8")
    env_hits = len(re.findall(r"STORAGE_PATH", text))
    db_names = set(re.findall(r"""['"]([^'"]+\.db)['"]""", text))
    if env_hits < 1:
        return "FAIL", "STORAGE_PATH not used"
    if len(db_names) > 1:
        return "FAIL", "multiple db files: " + ", ".join(sorted(db_names))
    extra_roots = [
        line
        for line in text.splitlines()
        if re.search(r"sqlite3\.connect\(|open\(.*\.db", line)
        and "STORAGE_PATH" not in line
        and "platform.db" not in line
        and not line.strip().startswith("#")
    ]
    if extra_roots:
        return "FAIL", "connect() outside STORAGE_PATH: " + extra_roots[0].strip()[:80]
    return "PASS", "one STORAGE_PATH root (%s)" % (next(iter(db_names), "platform.db"))


def check_ci_present_and_full_suite() -> Tuple[str, str]:
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        return "FAIL", ".github/workflows/ci.yml missing"
    text = ci.read_text(encoding="utf-8")
    run_lines = [
        line
        for line in text.splitlines()
        if "pytest" in line and not line.lstrip().startswith("#")
    ]
    if not run_lines:
        return "FAIL", "CI does not invoke pytest"
    has_full = any(
        ("python -m pytest tests" in line or "pytest tests" in line)
        and "not pilot" not in line
        for line in run_lines
    )
    if has_full:
        return "PASS", "CI runs pytest tests"
    if any("not pilot" in line for line in run_lines):
        return "FAIL", "CI wires only pytest -m not-pilot — not the full suite"
    return "FAIL", "CI pytest line is not a full suite"


def check_handler_bodies_distinct() -> Tuple[str, str]:
    actions = ROOT / "app" / "actions"
    if not actions.is_dir():
        return "FAIL", "app/actions missing"
    bodies: Dict[str, List[str]] = {}
    for path in sorted(actions.glob("*.py")):
        if path.name.startswith("_"):
            continue
        src = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return "FAIL", "%s does not parse" % path.name
        handle = None
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "handle":
                handle = node
                break
        if handle is None:
            continue
        chunk = ast.get_source_segment(src, handle) or ast.dump(handle)
        digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        bodies.setdefault(digest, []).append(path.name)
    twins = [names for names in bodies.values() if len(names) > 1]
    if twins:
        return "FAIL", "identical handle() bodies: " + ", ".join(twins[0])
    if len(bodies) < 2:
        return "PASS", "single handler — nothing to clone"
    return "PASS", "%d distinct handle() bodies" % len(bodies)


def check_health_fail_closed() -> Tuple[str, str]:
    missing = ROOT / ".acceptance-missing-disk"
    previous = os.environ.get("STORAGE_PATH")
    os.environ["STORAGE_PATH"] = str(missing)
    try:
        from app.health import evaluate_health

        code, body = evaluate_health()
    except Exception as exc:
        return "FAIL", "evaluate_health raised %s" % type(exc).__name__
    finally:
        # Restore so later checks (docker_health_200) probe the real disk,
        # not the poisoned path from this fail-closed probe.
        if previous is None:
            os.environ.pop("STORAGE_PATH", None)
        else:
            os.environ["STORAGE_PATH"] = previous
    if code == 200 or (isinstance(body, dict) and body.get("ok") is True):
        return "FAIL", "health stayed 200/ok when STORAGE_PATH is missing"
    if int(code) in (503, 500) and (not body.get("ok")):
        return "PASS", "HTTP %s fail-closed" % code
    return "FAIL", "health code=%s ok=%s" % (code, (body or {}).get("ok"))


def check_migration_no_create_all() -> Tuple[str, str]:
    """Schema belongs to alembic, not to boot.

    create_all() builds tables from whatever the models happen to say at
    start-up, so the migration becomes decoration and the first deploy
    against a real database diverges from what the tests ran on.
    """
    offenders = []
    for rel in ("app/store.py", "app/main.py", "app/db.py", "app/models.py"):
        path = ROOT / rel
        if path.is_file() and "create_all" in path.read_text(
            encoding="utf-8", errors="ignore"
        ):
            offenders.append(rel)
    versions = ROOT / "alembic" / "versions"
    if not versions.is_dir():
        return "FAIL", "alembic/versions missing: the schema is not migrated"
    revisions = sorted(versions.glob("*.py"))
    if not revisions:
        return "FAIL", "no alembic revision: the schema is not migrated"
    has_ddl = False
    for revision in revisions:
        text = revision.read_text(encoding="utf-8", errors="ignore")
        if "create_all" in text:
            offenders.append("alembic/versions/" + revision.name)
        if "op.create_table" in text:
            has_ddl = True
    if offenders:
        return "FAIL", "create_all in " + ", ".join(sorted(set(offenders)))
    if not has_ddl:
        return "FAIL", "no op.create_table in any revision: not real DDL"
    return "PASS", "%d revision(s), real DDL, no create_all" % len(revisions)


def _capability_stems() -> List[str]:
    actions = ROOT / "app" / "actions"
    if not actions.is_dir():
        return []
    return sorted(
        f.stem for f in actions.glob("*.py") if not f.stem.startswith("_")
    )


NEGATIVE_STATUS = re.compile(r"status_code\s*==\s*4\d\d")
NEGATIVE_CODE = re.compile(r"\b(?:400|401|403|404|409|422|429)\b")


def _negative_hits(text: str) -> int:
    """Count counter-case ASSERTIONS, not every mention of a number.

    Counting bare 4xx anywhere in a file made a 27KB shared route test hand
    its hits to every capability named in it, and a suite with nine
    counter-cases in total scored four-per-capability. A gate that passes
    what it exists to refuse is worse than no gate.
    """
    hits = 0
    for line in text.splitlines():
        stripped = line.strip()
        if "pytest.raises" in stripped:
            hits += 1
            continue
        if NEGATIVE_STATUS.search(stripped):
            hits += 1
            continue
        if stripped.startswith("assert") and NEGATIVE_CODE.search(stripped):
            hits += 1
    return hits


def check_negative_floor() -> Tuple[str, str]:
    """Four counter-cases per capability, attributed per TEST FUNCTION.

    Attribution is the whole difficulty. Counting hits in any file that
    merely mentions a capability credited every capability with the two big
    shared test files, so a suite with nine counter-cases in total scored
    four-per-capability and passed the gate that exists to refuse it. A
    counter-case counts for a capability only when the test that makes the
    assertion is the test that exercises the capability.
    """
    stems = _capability_stems()
    if not stems:
        return "FAIL", "no app/actions/: nothing to count against"
    tests = ROOT / "tests"
    if not tests.is_dir():
        return "FAIL", "no tests/"
    per = dict((stem, 0) for stem in stems)
    for path in sorted(tests.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            segment = ast.get_source_segment(text, node) or ""
            if not segment:
                continue
            hits = _negative_hits(segment)
            if not hits:
                continue
            for stem in stems:
                if stem in segment or stem in node.name:
                    per[stem] += hits
    thin = ["%s=%d" % (s, per[s]) for s in stems if per[s] < 4]
    if thin:
        return "FAIL", "under 4 counter-cases: " + ", ".join(thin)
    return "PASS", "%d capabilities, each with >=4 counter-cases" % len(stems)


def check_postgres_boot_200(http: _Http) -> Tuple[str, str]:
    """store.py routes through app.db, and DATABASE_URL is actually honoured.

    The old shape of this defect: DATABASE_URL read in the kernel config and
    used nowhere, while store.py held its own sqlite3 handle. The operator
    sets the variable, the platform accepts it without complaint and writes a
    SQLite file onto the container disk. Reading the variable somewhere is
    not the bar; the store taking its connection from one place is.
    """
    db = ROOT / "app" / "db.py"
    store = ROOT / "app" / "store.py"
    if not db.is_file():
        return "FAIL", "app/db.py missing: nothing decides the backend"
    db_text = db.read_text(encoding="utf-8", errors="ignore")
    if "DATABASE_URL" not in db_text:
        return "FAIL", "app/db.py does not read DATABASE_URL"
    if not store.is_file():
        return "FAIL", "app/store.py missing"
    store_text = store.read_text(encoding="utf-8", errors="ignore")
    routes = ("from app.db import" in store_text) or ("app.db" in store_text)
    opens_own = "sqlite3.connect(" in store_text or "create_engine(" in store_text
    if not routes:
        return (
            "FAIL",
            "app/store.py does not take its connection from app.db, so a set "
            "DATABASE_URL is read and ignored",
        )
    if opens_own:
        return (
            "FAIL",
            "app/store.py opens its own database beside app.db; one place must "
            "decide the backend or the two disagree",
        )
    measured = (os.environ.get("STORE_POSTGRES_BOOT") or "").strip()
    if measured == "200":
        resp = http.request("get", "/health")
        if resp.status_code != 200:
            return "FAIL", "postgres boot env=200 but /health is %s" % resp.status_code
        return "PASS", "store.py routes through app.db; boots on Postgres"
    # The gate owns the Postgres boot (it has the server). When it did not
    # measure, take the measurement this script can take: with a
    # DATABASE_URL configured, the platform must actually boot against that
    # database -- a set variable that the platform cannot dial is the
    # failure the check exists to catch. With no DATABASE_URL there is
    # nothing here to measure, and the check says exactly that.
    if not (os.environ.get("DATABASE_URL") or "").strip():
        return (
            "FAIL",
            "STORE_POSTGRES_BOOT=%r and DATABASE_URL unset "
            "(gate must boot it on Postgres)" % measured,
        )
    probe = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "with TestClient(app) as client:\n"
        "    print('POSTGRES_HEALTH', client.get('/health').status_code)\n"
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except Exception as exc:  # noqa: BLE001 - a failed measurement is a failed check
        return "FAIL", "Postgres boot raised %s: %s" % (type(exc).__name__, exc)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "POSTGRES_HEALTH 200" not in text:
        tail = " | ".join(line for line in text.strip().splitlines()[-3:])
        return "FAIL", "DATABASE_URL set but the platform did not boot on it: %s" % tail[:220]
    return "PASS", "store.py routes through app.db; boots on the configured DATABASE_URL"


def _smtp_live_roundtrip() -> Tuple[bool, str]:
    """A real socket round-trip through app.notify.deliver, to a local sink.

    This is the platform's own delivery path (smtplib, the configured-from-
    environment relay, the message it builds), not a fake caller. The sink
    only stands in for the receiving MTA; if the message does not arrive, the
    delivery path is broken and the drill says so.
    """
    import socket
    import socketserver
    import threading

    class _Sink(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

        def __init__(self, address):
            super().__init__(address, _SinkHandler)
            self.messages: List[str] = []

    class _SinkHandler(socketserver.StreamRequestHandler):
        """Minimal RFC 5321 dialogue: enough for smtplib.send_message.

        Greeting, multiline EHLO, MAIL/RCPT, DATA terminated by a lone dot,
        QUIT. STARTTLS is refused by name, so the drill connects with
        SMTP_STARTTLS=0 and the message body is what lands in ``messages``.
        """

        def handle(self) -> None:
            self.wfile.write(b"220 localhost acceptance sink\r\n")
            buffer: List[bytes] = []
            in_data = False
            while True:
                line = self.rfile.readline()
                if not line:
                    return
                if in_data:
                    if line.strip() == b".":
                        in_data = False
                        self.server.messages.append(
                            b"".join(buffer).decode("utf-8", "replace")
                        )
                        buffer = []
                        self.wfile.write(b"250 OK queued\r\n")
                    else:
                        buffer.append(line)
                    continue
                command = line.strip().upper()
                if command.startswith(b"EHLO"):
                    self.wfile.write(b"250-localhost\r\n250 SIZE 10485760\r\n")
                elif command.startswith(b"HELO"):
                    self.wfile.write(b"250 localhost\r\n")
                elif command.startswith(b"DATA"):
                    self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    in_data = True
                elif command.startswith(b"QUIT"):
                    self.wfile.write(b"221 Bye\r\n")
                    return
                elif command.startswith(b"MAIL") or command.startswith(b"RCPT"):
                    self.wfile.write(b"250 OK\r\n")
                elif command.startswith(b"RSET") or command.startswith(b"NOOP"):
                    self.wfile.write(b"250 OK\r\n")
                elif command.startswith(b"STARTTLS"):
                    self.wfile.write(b"502 STARTTLS not offered\r\n")
                else:
                    self.wfile.write(b"250 OK\r\n")

    server = _Sink(("127.0.0.1", 0))
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    keys = (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_STARTTLS",
        "SMTP_FROM",
        "SMTP_USER",
        "SMTP_PASS",
        "GUEST_WEBHOOK_URL",
    )
    saved = {key: os.environ.get(key) for key in keys}
    subject = "acceptance live-connector drill"
    try:
        os.environ.update(
            {
                "SMTP_HOST": "127.0.0.1",
                "SMTP_PORT": str(port),
                "SMTP_STARTTLS": "0",
                "SMTP_FROM": "acceptance@localhost",
            }
        )
        for key in ("SMTP_USER", "SMTP_PASS", "GUEST_WEBHOOK_URL"):
            os.environ.pop(key, None)
        from app.notify import deliver

        result = deliver(
            to="guest@example.com",
            subject=subject,
            body="acceptance drill: one live connector round-trip",
        )
        # smtplib closes the socket on context exit; the sink records on DATA.
        for _ in range(50):
            if server.messages:
                break
            import time

            time.sleep(0.02)
    except Exception as exc:  # noqa: BLE001 - a failed drill is a failed check
        return False, "%s: %s" % (type(exc).__name__, exc)
    finally:
        server.shutdown()
        server.server_close()
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if not isinstance(result, dict) or result.get("ok") is not True:
        return False, "deliver refused the drill: %s" % str(result)[:160]
    if result.get("transport") != "smtp":
        return False, "deliver used %r, not the configured SMTP path" % result.get("transport")
    arrived = [message for message in server.messages if subject in message]
    if not arrived:
        return False, "smtplib reported success but the sink received no message"
    return True, "smtp 127.0.0.1:%d accepted %d message(s)" % (port, len(arrived))


def check_one_live_connector() -> Tuple[str, str]:
    measured = (os.environ.get("STORE_LIVE_CONNECTOR") or "").strip()
    if measured:
        if measured.lower() in ("0", "false", "mocked", "no"):
            return "FAIL", "the only observed delivery was mocked (%s)" % measured
        return "PASS", "live delivery observed: %s" % measured
    ok, detail = _smtp_live_roundtrip()
    if not ok:
        return "FAIL", "no live delivery observed: %s" % detail
    return "PASS", "live delivery measured in-image: %s" % detail


def check_metrics_served(http: _Http) -> Tuple[str, str]:
    """Measured on the booted app. Shipping the module is not mounting it."""
    resp = http.request("get", "/metrics")
    if resp.status_code != 200:
        mounted = "mount_observability" in (
            (ROOT / "app" / "main.py").read_text(encoding="utf-8", errors="ignore")
            if (ROOT / "app" / "main.py").is_file()
            else ""
        )
        hint = (
            "app/main.py never calls mount_observability(app)"
            if not mounted
            else "mount_observability is called but /metrics does not answer"
        )
        return "FAIL", "GET /metrics is %s -- %s" % (resp.status_code, hint)
    try:
        body = resp.text
    except Exception:
        body = ""
    low = body.lower()
    if not any(k in low for k in ("count", "total", "requests")):
        return "FAIL", "/metrics answers 200 but reports no request count"
    if not any(k in low for k in ("latency", "duration", "seconds")):
        return "FAIL", "/metrics reports no latency"
    return "PASS", "/metrics serves a request count and latency"


def _scratch_value(column: str, cls: Any) -> Any:
    """A value the column accepts, from the model's own declared type."""
    constraints = (getattr(cls, "CONSTRAINTS", {}) or {}).get(column) or {}
    allowed = constraints.get("allowed_values") or []
    if allowed:
        return allowed[0]
    declared = ""
    annotations = getattr(cls, "__annotations__", {}) or {}
    raw = annotations.get(column)
    if raw is not None:
        declared = str(raw).lower()
    if declared in ("int", "float") or "int" in declared or "float" in declared:
        low = constraints.get("min")
        return low if isinstance(low, (int, float)) else 1
    return "sample"


def _backup_restore_drill() -> Tuple[bool, str]:
    """backup → wipe → restore on a scratch root, rows asserted both sides.

    Run against a temporary STORAGE_PATH so the drill cannot damage the
    acceptance database: the point is that the shipped backup/restore code
    moves rows, which is what the mounted-disk deployment depends on.
    """
    if not (ROOT / "app" / "backup.py").is_file():
        return False, "no app/backup.py"
    from app import store

    entity = next(iter(store.COLUMNS), "")
    if not entity:
        return False, "store.COLUMNS is empty: nothing to back up"
    keys = ("STORAGE_PATH", "BACKUP_DIR")
    saved = {key: os.environ.get(key) for key in keys}
    with tempfile.TemporaryDirectory(prefix="acceptance-drill-") as tmp:
        after = -1
        try:
            os.environ["STORAGE_PATH"] = tmp
            os.environ["BACKUP_DIR"] = str(Path(tmp) / "backups")
            from app import migrations

            migrations.upgrade_head()
            models = _models()
            cls = models.get(entity)
            record = {
                column: _scratch_value(column, cls) if cls is not None else "sample"
                for column in store.COLUMNS[entity]
            }
            store.save(entity, record, tenant_id="local")
            before = len(store.list_all(entity, tenant_id="local"))
            if before < 1:
                return False, "the scratch database did not accept a row"
            from app import backup

            archive = backup.create_backup()
            if not Path(archive).is_file() or Path(archive).stat().st_size == 0:
                return False, "create_backup produced no archive"
            backup.wipe_database()
            # The wiped database has no tables, so a read there answers with a
            # sqlite error rather than 0 rows -- that IS the wiped state.
            try:
                wiped = len(store.list_all(entity, tenant_id="local"))
            except Exception:
                wiped = 0
            if wiped != 0:
                return False, "wipe left %d row(s) behind" % wiped
            backup.restore_backup(archive)
            restored = store.list_all(entity, tenant_id="local")
            after = len(restored)
            if after and not any(
                str(row.get("reference")) == str(record.get("reference"))
                for row in restored
                if isinstance(row, dict)
            ):
                return False, "the restored row is not the row that was written"
        except Exception as exc:  # noqa: BLE001 - a failed drill is a failed check
            return False, "%s: %s" % (type(exc).__name__, exc)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    if after != before:
        return False, "restored %d row(s), wrote %d" % (after, before)
    return True, "%d row(s) survived backup → wipe → restore" % after


def check_backup_restore_roundtrip() -> Tuple[str, str]:
    measured = (os.environ.get("STORE_BACKUP_RESTORE") or "").strip().lower()
    if measured in ("ok", "pass", "1", "true"):
        return "PASS", "backup restored with rows intact"
    if measured:
        return "FAIL", "STORE_BACKUP_RESTORE=%r: a backup nobody restored is a file" % measured
    if not (ROOT / "app" / "backup.py").is_file():
        return "FAIL", "no app/backup.py"
    try:
        from app.db import database_url

        configured = database_url()
    except Exception:
        configured = ""
    if configured:
        # On Postgres the drill belongs to scripts/backup.sh (pg_dump/psql)
        # against a server this script does not own: drilling the SQLite path
        # here would report on a backend the operator is not running.
        return (
            "FAIL",
            "STORE_BACKUP_RESTORE unset and DATABASE_URL is set: restore the "
            "pg_dump this platform's scripts/backup.sh produces, or unset "
            "DATABASE_URL for the SQLite drill",
        )
    ok, detail = _backup_restore_drill()
    if not ok:
        return "FAIL", "backup drill failed: %s" % detail
    return "PASS", "measured in-image: %s" % detail


def check_bench_p95(http: _Http) -> Tuple[str, str]:
    measured = (os.environ.get("STORE_BENCH_P95_MS") or "").strip()
    if measured:
        try:
            value = float(measured)
        except ValueError:
            return "FAIL", "STORE_BENCH_P95_MS=%r is not a number" % measured
        if value >= 500.0:
            return "FAIL", "p95 %.0fms over the 500ms budget" % value
        return "PASS", "p95 %.0fms under 500ms" % value
    # A p95 over an unhealthy endpoint measures nothing. /health first, then
    # the number -- the budget is about a platform that answers.
    health = http.request("get", "/health")
    if health.status_code != 200:
        return "FAIL", "bench skipped: /health is %s, so a p95 would measure nothing" % health.status_code
    script = ROOT / "scripts" / "bench.py"
    if not script.is_file():
        return "FAIL", "scripts/bench.py missing: p95 was not measured"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except Exception as exc:  # noqa: BLE001 - a failed measurement is a failed check
        return "FAIL", "scripts/bench.py raised %s: %s" % (type(exc).__name__, exc)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"STORE_BENCH_P95_MS=([0-9.]+)", text)
    if not match:
        return "FAIL", "scripts/bench.py printed no p95 (exit %s)" % proc.returncode
    value = float(match.group(1))
    if value >= 500.0:
        return "FAIL", "p95 %.0fms over the 500ms budget" % value
    return "PASS", "measured in-image: p95 %.0fms under 500ms" % value


def check_audit_clean() -> Tuple[str, str]:
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        return "FAIL", ".github/workflows/ci.yml missing"
    text = ci.read_text(encoding="utf-8", errors="ignore").lower()
    missing = [t for t in ("pip-audit", "bandit") if t not in text]
    if missing:
        return "FAIL", "CI does not run " + ", ".join(missing)
    measured = (os.environ.get("STORE_AUDIT_CLEAN") or "").strip().lower()
    if measured in ("0", "false", "dirty"):
        return "FAIL", "pip-audit/bandit reported findings"
    return "PASS", "CI runs pip-audit and bandit"


def check_openapi_committed() -> Tuple[str, str]:
    path = ROOT / "docs" / "openapi.json"
    if not path.is_file():
        return "FAIL", "docs/openapi.json missing"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return "FAIL", "openapi is not JSON: %s" % exc
    if not str(doc.get("openapi") or "").startswith("3."):
        return "FAIL", "openapi version is not 3.x"
    paths = doc.get("paths")
    if not isinstance(paths, dict) or "/health" not in paths:
        return "FAIL", "openapi paths omit /health"
    v1 = [p for p in paths if str(p).startswith("/v1/")]
    if not v1:
        return "FAIL", "openapi has no /v1/ paths"
    return "PASS", "openapi 3.x with %d paths" % len(paths)


def check_docker_health_200(http: _Http) -> Tuple[str, str]:
    measured = (os.environ.get("STORE_DOCKER_HEALTH") or "").strip()
    if measured != "200":
        return "FAIL", "STORE_DOCKER_HEALTH=%r (Store gate must measure container /health=200)" % measured
    resp = http.request("get", "/health")
    if resp.status_code != 200:
        return "FAIL", "container health env=200 but GET /health is %s" % resp.status_code
    return "PASS", "docker health 200"


def check_cross_tenant_404(http: _Http) -> Tuple[str, str]:
    """Write as tenant A, read as tenant B: the read must be 404.

    404-not-403 is the platform's stated doctrine — cross-tenant access
    never leaks existence. A 200/403 here means the product is
    single-tenant by construction (the Phase-2 0.2 defect).
    """
    previous = os.environ.get("TENANT_TOKENS")
    os.environ["TENANT_TOKENS"] = "token-a:tenant-a,token-b:tenant-b"
    try:
        cap = _first_cap()
        if not cap:
            return "FAIL", "no first capability to POST"
        payload: Dict[str, Any] = {}
        models = _models()
        cls = models.get(cap)
        if cls is not None:
            constraints = getattr(cls, "CONSTRAINTS", {}) or {}
            for field in getattr(cls, "FIELDS", []) or []:
                rules = constraints.get(field) or {}
                if rules.get("allowed_values"):
                    payload[field] = rules["allowed_values"][0]
                elif rules.get("required"):
                    payload[field] = "sample"
        created = http.request(
            "post", "/v1/" + cap, json=payload,
            headers={"Authorization": "Bearer token-a"},
        )
        if created.status_code not in (200, 201):
            return "FAIL", "tenant A create: HTTP %s" % created.status_code
        body = {}
        try:
            body = created.json()
        except Exception:
            pass
        record = body.get("stored") or {}
        if not isinstance(record, dict) or not record.get("id"):
            return "FAIL", "tenant A create returned no stored id"
        read = http.request(
            "get", "/v1/%s/%s" % (cap, record["id"]),
            headers={"Authorization": "Bearer token-b"},
        )
        if read.status_code == 404:
            return "PASS", "tenant B read of tenant A record: HTTP 404"
        return "FAIL", "tenant B read returned HTTP %s (want 404)" % read.status_code
    finally:
        if previous is None:
            os.environ.pop("TENANT_TOKENS", None)
        else:
            os.environ["TENANT_TOKENS"] = previous


def check_authorship_floor() -> Tuple[str, str]:
    from app.factory.build.authorship import (  # type: ignore
        full_pilot_authorship_from,
    )

    # Prefer in-tree provenance so the product can judge itself without the
    # factory. Fall back to counting action modules tagged agent-written.
    receipt = {}
    for rel in ("docs/coder_receipt.json", "docs/build_provenance.json"):
        path = ROOT / rel
        if path.is_file():
            try:
                receipt.update(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    # No receipt means no receipt -- not "authored nothing". The factory
    # record (docs/coder_receipt.json, docs/build_provenance.json) is
    # internal and does not ship, so asking it here would fail every
    # delivered product. The stamp in each handler's own docstring is what
    # this check is ABOUT, it is in the tree, and it is what the floor line
    # asks the writer for. Judge the product by the product.
    try:
        floor = full_pilot_authorship_from(receipt, ROOT) if receipt else None
        if floor is not None and floor.meets_floor:
            return "PASS", "need≥%s action_py=%s cli=%s" % (
                floor.need,
                floor.action_py,
                len(floor.cli_authored_ids),
            )
        return "FAIL", "below floor need≥%s action_py=%s" % (floor.need, floor.action_py)
    except Exception:
        pass
    authored = 0
    actions = ROOT / "app" / "actions"
    if actions.is_dir():
        for path in actions.glob("*.py"):
            if path.name.startswith("_"):
                continue
            text = path.read_text(encoding="utf-8")
            if "CODER_MODEL" in text or "coding agent" in text.lower() or "coder CLI" in text:
                authored += 1
    n_required = receipt.get("n_required") or receipt.get("n_required_capabilities")
    try:
        n_required = int(n_required) if n_required is not None else None
    except (TypeError, ValueError):
        n_required = None
    need = 5 if n_required is None else min(5, max(1, int(n_required)))
    if authored >= need:
        return "PASS", "authored=%s need≥%s" % (authored, need)
    return "FAIL", "authored=%s below need≥%s" % (authored, need)


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    # A product that cannot boot must still produce a readable report: the
    # gate reads named PASS/FAIL lines, and a traceback on stderr is a
    # report nobody can act on. The client-dependent checks then fail with
    # the boot error as their detail, and the checks that do not need a
    # live app (tree, migrations, drills) still run.
    boot_error = ""
    try:
        http, cm = _client()
    except Exception as exc:  # noqa: BLE001 - reported as FAIL below
        http, cm = None, None
        boot_error = "%s: %s" % (type(exc).__name__, exc)
    results: List[Tuple[str, str, str]] = []
    try:
        # Generated from the floor, not written out here. A hand-kept list
        # is the second copy the floor file exists to abolish: it drifts the
        # moment a check is added, and the build is then graded against a
        # roster nobody updated. Order is the floor's order.
        import inspect as _inspect

        runners = []
        for _name in CHECKS:
            _fn = globals().get("check_" + _name)
            if _fn is None:
                runners.append(
                    (_name, (lambda n=_name: ("FAIL", "no check_%s in the harness" % n)))
                )
                continue
            if "http" in _inspect.signature(_fn).parameters:
                if http is None:
                    runners.append(
                        (
                            _name,
                            (
                                lambda n=_name: (
                                    "FAIL",
                                    "the platform did not boot: %s" % boot_error,
                                )
                            ),
                        )
                    )
                    continue
                runners.append((_name, (lambda f=_fn: f(http))))
            else:
                runners.append((_name, _fn))
        for name, fn in runners:
            try:
                status, detail = fn()
            except Exception as exc:
                status, detail = "FAIL", "%s: %s" % (type(exc).__name__, exc)
            results.append((name, status, detail))
            print("%s %s — %s" % (status, name, detail))
    finally:
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
    satisfied = sum(1 for _n, status, _d in results if status in {"PASS", "SKIP"})
    print("ACCEPTANCE: %d/%d" % (satisfied, REQUIRED))
    if results and results[-1][0] != "authorship_floor":
        print("FAIL harness — authorship_floor was not last")
        return 1
    if satisfied < REQUIRED or any(status == "FAIL" for _n, status, _d in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
