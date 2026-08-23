from __future__ import annotations

from .config import isoformat_utc, utc_now
from .ids import next_id


def log_decision(connection, *, entity_type, entity_id, actor, action, rationale):
    if not rationale.strip():
        raise ValueError("Karar gerekçesi boş olamaz")
    decision_id = next_id(connection, "decision_log")
    with connection:
        connection.execute("INSERT INTO decision_log(id,entity_type,entity_id,actor,action,rationale,created_at) VALUES(?,?,?,?,?,?,?)",
                           (decision_id,entity_type,entity_id,actor,action,rationale,isoformat_utc(utc_now())))
    return decision_id
