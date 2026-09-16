#!/usr/bin/env python3
"""Store-green acceptance — ≥12 measured checks. Presence-only is a fail.

Authorship floor is the LAST line. HTTP 200 ok:false is not a pass.
RAG skip policy: SKIP:no-rag-surface only when the product has no RAG
route or rag capability. Steward must plant + hit.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ['no_token_401', 'missing_field_422', 'enum_422', 'ui_served_200', 'rag_roundtrip_hit', 'single_persistence_root', 'ci_present_and_full_suite', 'handler_bodies_distinct', 'health_fail_closed', 'openapi_committed', 'docker_health_200', 'authorship_floor']
REQUIRED = 12


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


def check_rag_roundtrip_hit(http: _Http) -> Tuple[str, str]:
    if not _has_rag_surface():
        return "SKIP", "no-rag-surface"
    marker = "ACCEPTANCE-PLANT-%s copper kettle ordinance" % uuid.uuid4().hex[:8]
    ingest_paths = (
        "/v1/rag/ingest",
        "/v1/steward/rag/ingest",
        "/v1/dual_rag_sop",
        "/v1/dual_rag_estate_docs",
    )
    planted = False
    for path in ingest_paths:
        resp = http.request(
            "post",
            path,
            json={"text": marker, "content": marker, "paragraph": marker, "query": marker},
            headers=_auth(),
        )
        if resp.status_code in (200, 201, 202):
            planted = True
            break
    if not planted:
        return "FAIL", "RAG surface present but plant did not accept"
    query_paths = (
        "/v1/rag/query",
        "/v1/steward/rag/query",
        "/v1/rag/dual",
        "/v1/dual_rag_sop",
    )
    for path in query_paths:
        resp = http.request(
            "post",
            path,
            json={"q": "copper kettle ordinance", "query": "copper kettle ordinance", "text": marker},
            headers=_auth(),
        )
        if resp.status_code != 200:
            continue
        blob = (getattr(resp, "text", "") or "").lower()
        if "copper kettle" in blob or marker.lower() in blob:
            return "PASS", "plant+query hit via %s" % path
        try:
            data = resp.json()
        except Exception:
            data = {}
        hits = []
        if isinstance(data, dict):
            for key in ("hits", "results", "items", "matches", "chunks"):
                val = data.get(key)
                if isinstance(val, list) and val:
                    hits = val
        if hits:
            return "PASS", "plant+query returned %d hit(s) via %s" % (len(hits), path)
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
    try:
        floor = full_pilot_authorship_from(receipt, ROOT)
        if floor.meets_floor:
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
    http, cm = _client()
    results: List[Tuple[str, str, str]] = []
    try:
        runners = [
            ("no_token_401", lambda: check_no_token_401(http)),
            ("missing_field_422", lambda: check_missing_field_422(http)),
            ("enum_422", lambda: check_enum_422(http)),
            ("ui_served_200", lambda: check_ui_served_200(http)),
            ("rag_roundtrip_hit", lambda: check_rag_roundtrip_hit(http)),
            ("single_persistence_root", check_single_persistence_root),
            ("ci_present_and_full_suite", check_ci_present_and_full_suite),
            ("handler_bodies_distinct", check_handler_bodies_distinct),
            ("health_fail_closed", check_health_fail_closed),
            ("openapi_committed", check_openapi_committed),
            ("docker_health_200", lambda: check_docker_health_200(http)),
            ("authorship_floor", check_authorship_floor),
        ]
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
