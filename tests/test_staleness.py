from datetime import datetime, timezone

from src.claims import add_claim
from src.ingest import ingest
from src.staleness import stale_claim_ids


def test_t13_expired_claim_is_listed_not_deleted(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(connection, data=b"1,234 results for nursery wall art", source_family="AMAZON_KDP",
                    kind="MANUAL_PASTE", url="https://example.test", retrieved_at="2026-08-01T00:00:00+00:00", evidence_dir=evidence)
    claim = add_claim(connection, source_id=source.source_id, claim_type="AMZ_SEARCH_RESULT_COUNT",
                      subject="nursery", value_num=1234, unit="count", observed_at="2026-08-01",
                      quote="1,234 results for nursery wall art", evidence_dir=evidence)
    assert stale_claim_ids(connection, datetime(2026, 8, 9, tzinfo=timezone.utc)) == [claim.claim_id]
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 1
