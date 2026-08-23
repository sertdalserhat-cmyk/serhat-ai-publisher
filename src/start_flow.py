from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3

from .snapshot import verify_snapshots


@dataclass(frozen=True)
class StartResult:
    ready: bool
    claim_count: int
    unbound_count: int
    llm_call_count: int
    snapshot_failures: tuple[str, ...]
    opportunity_id: str | None
    opportunity_title: str | None
    opportunity_status: str | None
    next_action: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_start(conn: sqlite3.Connection, evidence_dir: Path) -> StartResult:
    """Evaluate the deterministic gates behind the user-facing BAŞLAT button."""
    claim_count = conn.execute(
        "SELECT COUNT(*) FROM claim WHERE status='ACTIVE'"
    ).fetchone()[0]
    unbound_count = conn.execute(
        "SELECT COUNT(*) FROM claim WHERE status='ACTIVE' AND opportunity_id IS NULL"
    ).fetchone()[0]
    llm_call_count = conn.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0]
    opportunity = conn.execute(
        """
        SELECT id, title, status
        FROM opportunity
        ORDER BY CASE WHEN is_active=1 THEN 0 ELSE 1 END, created_at DESC
        LIMIT 1
        """
    ).fetchone()
    failures = tuple(verify_snapshots(conn, evidence_dir))

    ready = bool(
        claim_count >= 30
        and unbound_count == 0
        and llm_call_count == 0
        and not failures
        and opportunity
        and opportunity["status"] in {"READY_FOR_REVIEW", "APPROVED", "BUILD"}
    )
    if failures:
        next_action = "FIX_SNAPSHOTS"
    elif claim_count < 30:
        next_action = "COLLECT_EVIDENCE"
    elif unbound_count:
        next_action = "BIND_CLAIMS"
    elif not opportunity:
        next_action = "CREATE_OPPORTUNITY"
    elif ready:
        next_action = "REVIEW_OPPORTUNITY"
    else:
        next_action = "PREPARE_REVIEW"

    return StartResult(
        ready=ready,
        claim_count=claim_count,
        unbound_count=unbound_count,
        llm_call_count=llm_call_count,
        snapshot_failures=failures,
        opportunity_id=opportunity["id"] if opportunity else None,
        opportunity_title=opportunity["title"] if opportunity else None,
        opportunity_status=opportunity["status"] if opportunity else None,
        next_action=next_action,
    )
