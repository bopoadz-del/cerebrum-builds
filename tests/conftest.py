"""Test bootstrap for the generated platform.

Puts the platform root on sys.path and points persistence at a scratch
directory, so running the suite never touches a real data file.

STORAGE_PATH is FORCED, not defaulted. The build environment legitimately
carries its own STORAGE_PATH (the factory backend sets one), and a
``setdefault`` here made every tester round share one database file: a
table created by round N rejected round N+1's columns, and the rework loop
burned its budget chasing schema errors no round had actually caused.

Outbound network is BLOCKED, not merely unconfigured. Stripping the store
env only proves the platform does not call the store; a handler that posts
to an arbitrary public URL still passed, and one did -- "sent" a webhook to
the open internet from a platform whose whole claim is running offline.
Loopback stays open so TestClient-style local servers keep working.
P1: this blocker is unchanged. Do not add local-inference or cloud hosts.
"""

import os
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["STORAGE_PATH"] = tempfile.mkdtemp(prefix="platform-test-")

# Settings the operator supplies at deploy time are not a build failure. This
# must run BEFORE the first import of ``app`` below: a product that reads a
# required credential at import would otherwise KeyError inside the factory's
# own tests. Shared, word for word, with scripts/acceptance.py.
DEPLOY_TIME_PLACEHOLDER = "set-at-deploy"


def _stand_in_for_deploy_time_settings(root):
    """Give every setting the product REQUIRES, and the build cannot have, a
    stand-in -- so importing the product does not KeyError on a credential its
    operator supplies at deploy time. Returns the names stood in for."""
    import ast as _ast
    import os as _os
    from pathlib import Path as _Path

    root = _Path(root)
    examples = {}
    env_example = root / ".env.example"
    if env_example.is_file():
        for raw in env_example.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.split(" #", 1)[0].strip().strip("'\"")
            if key.strip():
                examples[key.strip()] = value

    def _is_environ(node):
        if isinstance(node, _ast.Attribute) and node.attr == "environ":
            return isinstance(node.value, _ast.Name) and node.value.id == "os"
        return isinstance(node, _ast.Name) and node.id == "environ"

    required = set()
    app_dir = root / "app"
    if app_dir.is_dir():
        for path in app_dir.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = _ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, ValueError):
                continue
            for node in _ast.walk(tree):
                if (
                    isinstance(node, _ast.Subscript)
                    and isinstance(node.ctx, _ast.Load)
                    and _is_environ(node.value)
                    and isinstance(node.slice, _ast.Constant)
                    and isinstance(node.slice.value, str)
                ):
                    required.add(node.slice.value)

    stood_in = []
    for name in sorted(required):
        if name not in _os.environ:
            _os.environ[name] = examples.get(name) or DEPLOY_TIME_PLACEHOLDER
            stood_in.append(name)
    return stood_in
_stand_in_for_deploy_time_settings(Path(__file__).resolve().parents[1])

# Schema is versioned. connect() does not CREATE TABLE. Apply head so
# model/route tests have tables; a missing revision fails the suite.
# ImportError is only for isolation probes that exec this file without app/.
try:
    from app.migrations import upgrade_head  # noqa: E402

    upgrade_head()
except ImportError:
    pass

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_real_connect = socket.socket.connect


def _offline_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, (bytes, bytearray)):
        host = host.decode("utf-8", "replace")
    if str(host) not in _LOCAL_HOSTS:
        raise OSError(
            f"offline suite: outbound connection to {host!r} refused -- this "
            "platform must run with no network"
        )
    return _real_connect(self, address)


socket.socket.connect = _offline_connect


def pytest_configure(config):
    """Register the factory vs pilot split. TESTER's lane is tests/** so
    this cannot live in a repo-root pytest.ini."""
    config.addinivalue_line(
        "markers",
        "pilot: Store-backed execute-all; excluded from the factory code-phase gate",
    )
