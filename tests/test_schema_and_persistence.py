"""Schema belongs to alembic; one storage root; no DDL at connect time."""

from __future__ import annotations

from pathlib import Path

from app import store
from app.models import CAPABILITY_IDS, MODELS

ROOT = Path(__file__).resolve().parents[1]


def test_every_capability_has_a_table_of_its_own_name():
    conn = store.connect()
    try:
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    finally:
        conn.close()
    for capability in CAPABILITY_IDS:
        assert capability in names, capability


def test_each_table_carries_a_tenant_column():
    conn = store.connect()
    try:
        for capability in CAPABILITY_IDS:
            columns = {
                row[1] for row in conn.execute(f"PRAGMA table_info({capability})").fetchall()
            }
            assert "tenant_id" in columns, capability
            assert {"id", "created_at", "updated_at"} <= columns
            for field in MODELS[capability].FIELDS:
                assert field in columns, (capability, field)
    finally:
        conn.close()


def test_the_migration_declares_real_ddl_and_no_create_all():
    source = (ROOT / "alembic" / "versions" / "0001_baseline.py").read_text(encoding="utf-8")
    assert source.count("op.create_table(") == len(CAPABILITY_IDS)
    assert "create_all" not in source
    store_source = (ROOT / "app" / "store.py").read_text(encoding="utf-8")
    assert "CREATE TABLE" not in store_source
    assert "app.db" in store_source
    assert "sqlite3.connect(" not in store_source


def test_one_storage_root():
    root = Path(store.storage_root())
    assert store.db_path().parent == root
    assert store.db_path().name == "platform.db"


def test_the_store_refuses_an_entity_it_does_not_declare():
    import pytest

    with pytest.raises(KeyError):
        store.save("not_a_capability", {"reference": "r"}, "psi")
    with pytest.raises(ValueError):
        store.save("notification", {"reference": "r"}, "")


def test_a_connection_does_not_create_domain_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "fresh"))
    conn = store.connect()
    try:
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    finally:
        conn.close()
    assert not (names & set(CAPABILITY_IDS))
