from pathlib import Path

from src.start_flow import evaluate_start


def test_start_requires_thirty_bound_claims(connection, tmp_path: Path):
    result = evaluate_start(connection, tmp_path)
    assert result.ready is False
    assert result.claim_count == 0
    assert result.next_action == "COLLECT_EVIDENCE"


def test_start_reports_missing_snapshot(connection, tmp_path: Path):
    with connection:
        connection.execute(
            """INSERT INTO source
            (id, source_family, kind, retrieved_at, ingested_at, raw_hash,
             snapshot_path, content_type, byte_size, reliability, legal_status,
             ttl_days, collector)
            VALUES ('src_000001','MANUAL_ENTRY','TEXT','2026-08-24T00:00:00+03:00',
                    '2026-08-24T00:00:00+03:00','deadbeef','missing.txt',
                    'text/plain',1,'MEDIUM','ALLOWED',30,'human:serhat')"""
        )
    result = evaluate_start(connection, tmp_path)
    assert result.snapshot_failures == ("src_000001",)
    assert result.next_action == "FIX_SNAPSHOTS"
