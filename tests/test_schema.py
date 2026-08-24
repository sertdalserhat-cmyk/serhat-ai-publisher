from __future__ import annotations

from src.db import initialize


def test_t01_init_is_idempotent_and_preserves_data(db_path):
    first = initialize(db_path)
    first.execute("INSERT INTO meta(key, value) VALUES('sentinel', 'kept')")
    first.commit()
    db_uuid = first.execute(
        "SELECT value FROM meta WHERE key='db_uuid'"
    ).fetchone()[0]
    first.close()

    second = initialize(db_path)
    assert second.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()[0] == "1"
    assert second.execute(
        "SELECT value FROM meta WHERE key='sentinel'"
    ).fetchone()[0] == "kept"
    assert second.execute(
        "SELECT value FROM meta WHERE key='db_uuid'"
    ).fetchone()[0] == db_uuid
    assert second.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    second.close()
