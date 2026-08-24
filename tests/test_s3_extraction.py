import os

import pytest

from src.cost import LLMDisabledError, record_llm_call
from src.extraction import (
    ClaimCandidate,
    DeterministicDryRunExtractor,
    apply_candidate_decision,
    render_candidate_review,
    run_claim_extraction,
    validate_claim_candidate,
)
from src.ingest import ingest
from src.opportunity import create_opportunity
from src.report import generate_report


class CountingExtractor:
    def __init__(self):
        self.calls = 0

    def extract(self, request):
        self.calls += 1
        return []


class FixedExtractor:
    def __init__(self, proposals):
        self.proposals = proposals

    def extract(self, request):
        return self.proposals


def test_s3_t01_disabled_budget_prevents_extractor_call_and_claim_write(connection):
    extractor = CountingExtractor()
    before = connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0]

    with pytest.raises(LLMDisabledError, match="kapalı"):
        run_claim_extraction(
            connection,
            source_id="src_not_reached",
            extractor=extractor,
            llm_enabled=False,
        )

    assert extractor.calls == 0
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == before
    assert connection.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0] == 0


def test_s3_t02_exact_text_quote_accepts_candidate_without_writing(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"1,234 results for nursery wall art\nSpace Nursery Print Set",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/search",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_SEARCH_RESULT_COUNT",
        subject="nursery wall art",
        value_num=1234,
        unit="count",
        observed_at="2026-08-23",
        quote="1,234 results for nursery wall art",
    )

    assert validate_claim_candidate(
        connection, candidate, evidence_dir=evidence
    ) == candidate
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t03_quote_absent_from_snapshot_is_rejected(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Invented price is 12.99 USD",
    )

    with pytest.raises(ValueError, match="birebir"):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


@pytest.mark.parametrize("source_id", ["", "src_999999"])
def test_s3_t04_missing_or_unknown_source_is_rejected(connection, tmp_path, source_id):
    candidate = ClaimCandidate(
        source_id=source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )

    with pytest.raises(ValueError, match="source_id"):
        validate_claim_candidate(connection, candidate, evidence_dir=tmp_path)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t05_claim_type_outside_closed_vocabulary_is_rejected(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed demand score is 99",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="INVENTED_DEMAND_SCORE",
        subject="example book",
        value_num=99,
        unit="score",
        observed_at="2026-08-23",
        quote="Observed demand score is 99",
    )

    with pytest.raises(ValueError, match="Geçersiz claim_type"):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("value_num", "unit", "quote", "message"),
    [
        (None, "USD", "Observed listing price is 12.99 USD", "sayısal değer"),
        (12.99, "EUR", "Observed listing price is 12.99 USD", "geçerli birim"),
        (12.99, "USD", "Observed listing price is unavailable", "value_num"),
        (12.99, "USD", "12.99", "12 karakter"),
    ],
)
def test_s3_t06_numeric_value_unit_and_quote_context_are_required(
    connection, tmp_path, value_num, unit, quote, message
):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=value_num,
        unit=unit,
        observed_at="2026-08-23",
        quote=quote,
    )

    with pytest.raises(ValueError, match=message):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t07_observed_at_after_source_retrieval_is_rejected(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-24",
        quote="Observed listing price is 12.99 USD",
    )

    with pytest.raises(ValueError, match="observed_at"):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t08_tampered_snapshot_is_rejected(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    relative = connection.execute(
        "SELECT snapshot_path FROM source WHERE id=?", (source.source_id,)
    ).fetchone()[0]
    snapshot = evidence / relative
    os.chmod(snapshot, 0o644)
    snapshot.write_bytes(b"tampered evidence")
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )

    with pytest.raises(ValueError, match="hash"):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t09_screenshot_requires_locator_and_caps_confidence(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"\x89PNG\r\n\x1a\nraw-evidence",
        source_family="AMAZON_KDP",
        kind="MANUAL_SCREENSHOT",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
        file_name="shot.png",
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_BSR",
        subject="example book",
        value_num=48210,
        unit="rank",
        observed_at="2026-08-23",
        confidence="HIGH",
    )

    with pytest.raises(ValueError, match="locator"):
        validate_claim_candidate(connection, candidate, evidence_dir=evidence)
    validated = validate_claim_candidate(
        connection,
        ClaimCandidate(**{**candidate.__dict__, "locator": "Best Sellers Rank satırı"}),
        evidence_dir=evidence,
    )
    assert validated.confidence == "MEDIUM"
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t10_extractor_output_cannot_write_claim_directly(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )

    proposals = run_claim_extraction(
        connection,
        source_id=source.source_id,
        extractor=FixedExtractor([candidate]),
        llm_enabled=True,
        evidence_dir=evidence,
    )

    assert proposals == [candidate]
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0


def test_s3_t11_human_rejection_leaves_claim_count_unchanged(connection, tmp_path):
    candidate = ClaimCandidate(
        source_id="not_evaluated_on_reject",
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )
    before = connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0]

    result = apply_candidate_decision(
        connection,
        candidate,
        approved=False,
        extracted_by="extractor:dry-run-v1",
        evidence_dir=tmp_path,
    )

    assert result is None
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == before


def test_s3_t12_human_approval_persists_claim_with_extractor_version(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )

    result = apply_candidate_decision(
        connection,
        candidate,
        approved=True,
        extracted_by="extractor:dry-run-v1",
        evidence_dir=evidence,
    )

    row = connection.execute("SELECT * FROM claim WHERE id=?", (result.claim_id,)).fetchone()
    assert row["source_id"] == source.source_id
    assert row["quote"] == candidate.quote
    assert row["extracted_by"] == "extractor:dry-run-v1"
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 1


def test_s3_t13_reprocessing_same_approved_candidate_is_idempotent(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )

    first = apply_candidate_decision(
        connection, candidate, approved=True,
        extracted_by="extractor:dry-run-v1", evidence_dir=evidence,
    )
    second = apply_candidate_decision(
        connection, candidate, approved=True,
        extracted_by="extractor:dry-run-v1", evidence_dir=evidence,
    )

    assert second.claim_id == first.claim_id
    assert second.warning
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 1


@pytest.mark.parametrize(
    "output",
    [
        "{not-json",
        '[{"source_id":"src_000001","claim_type":"AMZ_PRICE"}]',
    ],
)
def test_s3_t14_invalid_json_or_missing_fields_produces_zero_writes(
    connection, tmp_path, output
):
    with pytest.raises(ValueError, match="JSON|şeması"):
        run_claim_extraction(
            connection,
            source_id="src_000001",
            extractor=FixedExtractor(output),
            llm_enabled=True,
            evidence_dir=tmp_path,
        )
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0] == 0


def test_s3_t15_enabled_successful_call_writes_complete_audit_record(connection):
    call_id = record_llm_call(
        connection,
        llm_enabled=True,
        task_key="S3_CLAIM_EXTRACTION",
        model="deterministic-test-model",
        in_tokens=120,
        out_tokens=45,
        cost_usd=0.0012,
        pricing_ver="test-v1",
        schema_valid=True,
        retry_count=0,
        input_hash="a" * 64,
    )

    row = connection.execute("SELECT * FROM llm_call WHERE id=?", (call_id,)).fetchone()
    assert dict(row) == {
        "id": call_id,
        "task_key": "S3_CLAIM_EXTRACTION",
        "model": "deterministic-test-model",
        "in_tokens": 120,
        "out_tokens": 45,
        "cost_usd": 0.0012,
        "pricing_ver": "test-v1",
        "schema_valid": 1,
        "retry_count": 0,
        "input_hash": "a" * 64,
        "created_at": row["created_at"],
    }


def test_s3_t16_approved_claim_report_has_zero_unbound_claims(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    opportunity_id = create_opportunity(
        connection,
        title="S-3 acceptance",
        channel="KDP",
        product_type="book",
        niche="s3 acceptance fixture",
    )
    candidate = ClaimCandidate(
        source_id=source.source_id,
        claim_type="AMZ_PRICE",
        subject="example book",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
    )
    apply_candidate_decision(
        connection,
        candidate,
        approved=True,
        extracted_by="extractor:dry-run-v1",
        evidence_dir=evidence,
        opportunity_id=opportunity_id,
    )

    report = generate_report(
        connection,
        opportunity_id=opportunity_id,
        out_path=tmp_path / "s3-report.html",
    ).read_text(encoding="utf-8")
    assert "Bağsız iddia sayısı: 0" in report
    assert connection.execute(
        "SELECT COUNT(*) FROM claim WHERE opportunity_id IS NULL"
    ).fetchone()[0] == 0


def test_dry_run_renders_human_review_without_network_cost_or_writes(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(
        connection,
        data=b"Observed listing price is 12.99 USD",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/item",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    output = (
        '[{"source_id":"' + source.source_id + '",'
        '"claim_type":"AMZ_PRICE","subject":"example book",'
        '"observed_at":"2026-08-23","value_num":12.99,"unit":"USD",'
        '"quote":"Observed listing price is 12.99 USD"}]'
    )
    proposals = run_claim_extraction(
        connection,
        source_id=source.source_id,
        extractor=DeterministicDryRunExtractor(output),
        llm_enabled=False,
        evidence_dir=evidence,
    )
    review = render_candidate_review(proposals)

    assert "İNSAN ONAYI GEREKİR" in review
    assert "Karar: BEKLİYOR" in review
    assert source.source_id in review
    assert "12.99 USD" in review
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0] == 0
