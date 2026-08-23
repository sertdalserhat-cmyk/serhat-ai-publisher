import sqlite3

import pytest

from src.decisions import log_decision


def test_t16_decision_log_is_append_only(connection):
    did = log_decision(connection, entity_type="SYSTEM", entity_id=None, actor="system", action="CREATE", rationale="test")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("UPDATE decision_log SET rationale='changed' WHERE id=?", (did,))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("DELETE FROM decision_log WHERE id=?", (did,))
