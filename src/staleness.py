from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import utc_now
from .vocab import require_claim_type


def _dt(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def stale_claim_ids(connection, now=None):
    current = now or utc_now()
    stale = []
    rows = connection.execute("SELECT c.id,c.claim_type,s.retrieved_at FROM claim c JOIN source s ON s.id=c.source_id")
    for row in rows:
        ttl = require_claim_type(row["claim_type"]).ttl_days
        if ttl and current > _dt(row["retrieved_at"]) + timedelta(days=ttl):
            stale.append(row["id"])
    return stale
