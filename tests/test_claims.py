from __future__ import annotations

import sqlite3

import pytest

from src.claims import add_claim
from src.ingest import ingest


@pytest.fixture
def text_source(connection, tmp_path):
    evidence = tmp_path / "evidence"
    result = ingest(
        connection, data=b"1,234 results for nursery wall art\nSpace Nursery Print Set",
        source_family="AMAZON_KDP", kind="MANUAL_PASTE",
        url="https://example.test/search", retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    return result.source_id, evidence


def base(source_id, evidence):
    return dict(source_id=source_id, claim_type="AMZ_SEARCH_RESULT_COUNT",
                subject="nursery wall art", value_num=1234, unit="count",
                observed_at="2026-08-23", evidence_dir=evidence)


def test_t04_source_id_is_required(connection, tmp_path):
    with pytest.raises(ValueError, match="CB-1"):
        add_claim(connection, **base(None, tmp_path))
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_t05_invalid_source_proves_fk_is_enabled(connection, tmp_path):
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        add_claim(connection, **base("src_999999", tmp_path))


def test_t07_numeric_value_is_required(connection, text_source):
    source_id, evidence = text_source
    args = base(source_id, evidence)
    args["value_num"] = None
    with pytest.raises(ValueError, match="CB-2"):
        add_claim(connection, **args)


def test_t08_quote_must_be_exact_snapshot_substring(connection, text_source):
    source_id, evidence = text_source
    with pytest.raises(ValueError, match="CB-4"):
        add_claim(connection, **base(source_id, evidence), quote="1,234 invented context")


def test_t09_observed_at_cannot_follow_retrieval(connection, text_source):
    source_id, evidence = text_source
    args = base(source_id, evidence)
    args["observed_at"] = "2026-08-24"
    with pytest.raises(ValueError, match="CB-3"):
        add_claim(connection, **args, quote="1,234 results for nursery wall art")


def test_date_only_observation_uses_source_local_calendar_date(connection, tmp_path):
    from src.ingest import ingest
    evidence=tmp_path/"evidence"
    source=ingest(connection,data=b"screenshot",source_family="ETSY",kind="MANUAL_SCREENSHOT",
                  url="https://example.test",locale="TR",retrieved_at="2026-08-24T02:07:00+03:00",
                  evidence_dir=evidence,file_name="shot.png")
    result=add_claim(connection,source_id=source.source_id,claim_type="ETSY_LISTING_COUNT",
                     subject="nursery",value_num=1000,unit="count",observed_at="2026-08-24",
                     locator="arama üst satırı",evidence_dir=evidence)
    assert result.claim_id == "clm_000001"


def test_t10_duplicate_claim_is_rejected(connection, text_source):
    source_id, evidence = text_source
    args = base(source_id, evidence)
    add_claim(connection, **args, quote="1,234 results for nursery wall art")
    with pytest.raises(ValueError, match="zaten"):
        add_claim(connection, **args, quote="1,234 results for nursery wall art")
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 1


def test_t19_numeric_quote_requires_number_and_context(connection, text_source):
    source_id, evidence = text_source
    args = base(source_id, evidence)
    with pytest.raises(ValueError, match="value_num"):
        add_claim(connection, **args, quote="nursery wall art context")
    with pytest.raises(ValueError, match="12 karakter"):
        add_claim(connection, **args, quote="1,234")
    result = add_claim(connection, **args, quote="1,234 results for nursery wall art")
    assert result.claim_id == "clm_000001"


def test_t20_screenshot_caps_confidence_and_requires_locator(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection, data=b"\x89PNG\r\n\x1a\nnot-real-image-but-raw-evidence",
        source_family="AMAZON_KDP", kind="MANUAL_SCREENSHOT",
        url="https://example.test/item", retrieved_at="2026-08-23T14:20:00+00:00",
        evidence_dir=evidence, file_name="shot.png",
    )
    args = dict(source_id=source.source_id, claim_type="AMZ_BSR", subject="B0EXAMPLE",
                value_num=48210, unit="rank", observed_at="2026-08-23",
                confidence="HIGH", evidence_dir=evidence)
    with pytest.raises(ValueError, match="locator"):
        add_claim(connection, **args)
    result = add_claim(connection, **args, locator="ürün detay sayfası, Best Sellers Rank satırı")
    assert result.confidence == "MEDIUM"
    assert result.warning
