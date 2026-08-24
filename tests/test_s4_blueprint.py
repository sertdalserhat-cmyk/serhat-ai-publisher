from dataclasses import replace

import pytest

from src.blueprint import (
    BlueprintCandidate,
    DeterministicBlueprintExtractor,
    EvidenceStatement,
    apply_blueprint_decision,
    generate_blueprint_report,
    run_blueprint_generation,
    validate_blueprint_candidate,
)
from src.claims import add_claim
from src.ingest import ingest
from src.opportunity import create_opportunity


def candidate(opportunity_id: str) -> BlueprintCandidate:
    return BlueprintCandidate(
        opportunity_id=opportunity_id,
        working_title="Evidence-led activity book",
        target_reader="Parents of preschool children",
        reader_problem="Needs structured screen-free activities",
        product_promise="A guided set of age-appropriate activities",
        format="paperback",
        language="English",
        market="US",
        differentiators=("Evidence-led positioning",),
        content_outline=("Introduction", "Activities"),
        risks=("Demand size is UNKNOWN",),
        unknowns=("Conversion rate",),
        evidence_claim_ids=("clm_000001",),
        evidence_statements=(
            EvidenceStatement("Observed price signal", ("clm_000001",)),
        ),
    )


@pytest.mark.parametrize("status", ["DRAFT", "RESEARCHING", "READY_FOR_REVIEW", "REJECTED", "PARKED"])
def test_s4_t01_non_approved_opportunity_is_rejected(connection, status):
    opportunity_id = create_opportunity(
        connection,
        title=f"Blueprint {status}",
        channel="KDP",
        product_type="book",
        niche=f"blueprint fixture {status}",
    )
    if status != "DRAFT":
        connection.execute(
            "UPDATE opportunity SET status=? WHERE id=?", (status, opportunity_id)
        )
        connection.commit()

    with pytest.raises(ValueError, match="APPROVED"):
        validate_blueprint_candidate(connection, candidate(opportunity_id))


def test_s4_t02_approved_opportunity_without_active_claim_is_rejected(connection):
    opportunity_id = create_opportunity(
        connection,
        title="Approved without evidence",
        channel="KDP",
        product_type="book",
        niche="approved without evidence fixture",
    )
    connection.execute(
        "UPDATE opportunity SET status='APPROVED' WHERE id=?", (opportunity_id,)
    )
    connection.commit()

    with pytest.raises(ValueError, match="aktif claim"):
        validate_blueprint_candidate(connection, candidate(opportunity_id))


def approved_opportunity_with_claim(connection, tmp_path, suffix):
    evidence = tmp_path / f"evidence-{suffix}"
    source = ingest(
        connection,
        data=f"Observed listing price is 12.99 USD {suffix}".encode(),
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url=f"https://example.test/{suffix}",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    opportunity_id = create_opportunity(
        connection,
        title=f"Approved {suffix}",
        channel="KDP",
        product_type="book",
        niche=f"approved blueprint fixture {suffix}",
    )
    connection.execute(
        "UPDATE opportunity SET status='APPROVED' WHERE id=?", (opportunity_id,)
    )
    claim = add_claim(
        connection,
        source_id=source.source_id,
        opportunity_id=opportunity_id,
        claim_type="AMZ_PRICE",
        subject=f"book {suffix}",
        value_num=12.99,
        unit="USD",
        observed_at="2026-08-23",
        quote="Observed listing price is 12.99 USD",
        evidence_dir=evidence,
    )
    return opportunity_id, claim.claim_id


def test_s4_t03_unknown_or_foreign_claim_reference_is_rejected(connection, tmp_path):
    first_opp, first_claim = approved_opportunity_with_claim(connection, tmp_path, "first")
    _, foreign_claim = approved_opportunity_with_claim(connection, tmp_path, "second")

    for invalid_ids in (("clm_999999",), (foreign_claim,)):
        proposal = replace(
            candidate(first_opp), evidence_claim_ids=invalid_ids
        )
        with pytest.raises(ValueError, match="başka fırsata"):
            validate_blueprint_candidate(connection, proposal)

    assert validate_blueprint_candidate(
        connection,
        replace(
            candidate(first_opp),
            evidence_claim_ids=(first_claim,),
            evidence_statements=(EvidenceStatement("Observed price signal", (first_claim,)),),
        ),
    ).opportunity_id == first_opp


def test_s4_t04_each_evidence_statement_requires_valid_claim_ids(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(connection, tmp_path, "mapped")
    base = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
    )

    for statements in (
        (),
        (EvidenceStatement("Observed price signal", ()),),
        (EvidenceStatement("Observed price signal", ("clm_999999",)),),
    ):
        with pytest.raises(ValueError, match="S4-T04"):
            validate_blueprint_candidate(
                connection, replace(base, evidence_statements=statements)
            )

    valid = replace(
        base,
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )
    assert validate_blueprint_candidate(connection, valid) == valid


@pytest.mark.parametrize(
    "field",
    [
        "working_title",
        "target_reader",
        "reader_problem",
        "product_promise",
        "format",
        "language",
        "market",
    ],
    ids=["title", "reader", "problem", "promise", "format", "language", "market"],
)
def test_s4_t05_missing_required_field_produces_zero_writes(connection, tmp_path, field):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "req"
    )
    valid = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )
    invalid = replace(valid, **{field: " "})
    before_decisions = connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
    before_claims = connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0]

    with pytest.raises(ValueError, match="S4-T05"):
        validate_blueprint_candidate(connection, invalid)

    assert connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == before_decisions
    assert connection.execute("SELECT COUNT(*) FROM claim").fetchone()[0] == before_claims


@pytest.mark.parametrize("unknowns", [(), ("",), (" ",)])
def test_s4_t06_unknown_fields_cannot_be_silently_removed(connection, tmp_path, unknowns):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "unknowns"
    )
    proposal = replace(
        candidate(opportunity_id),
        unknowns=unknowns,
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )

    with pytest.raises(ValueError, match="UNKNOWN"):
        validate_blueprint_candidate(connection, proposal)


def test_s4_t07_dry_run_has_no_network_cost_or_persistent_write(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "dry"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )
    before_decisions = connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]

    result = run_blueprint_generation(
        connection,
        opportunity_id=opportunity_id,
        extractor=DeterministicBlueprintExtractor(proposal),
        llm_enabled=False,
    )

    assert result == proposal
    assert connection.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == before_decisions
    assert connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='product_blueprint'"
    ).fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM product_blueprint").fetchone()[0] == 0


class FixedBlueprintExtractor:
    def __init__(self, proposal):
        self.proposal = proposal

    def generate(self, request):
        return self.proposal


def test_s4_t08_extractor_output_cannot_persist_blueprint_directly(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "model"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )

    result = run_blueprint_generation(
        connection,
        opportunity_id=opportunity_id,
        extractor=FixedBlueprintExtractor(proposal),
        llm_enabled=True,
    )

    assert result == proposal
    assert connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='product_blueprint'"
    ).fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM product_blueprint").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == 0


def test_s4_t09_human_rejection_produces_zero_persistent_writes(connection):
    proposal = candidate("not-evaluated-on-reject")
    before_decisions = connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]

    result = apply_blueprint_decision(
        connection, proposal, approved=False, actor="human:serhat"
    )

    assert result is None
    assert connection.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == before_decisions
    assert connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='product_blueprint'"
    ).fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM product_blueprint").fetchone()[0] == 0


def test_s4_t10_human_approval_persists_blueprint_evidence_and_decision(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "approve"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )

    blueprint_id = apply_blueprint_decision(
        connection,
        proposal,
        approved=True,
        actor="human:serhat",
        rationale="Kullanıcı kanıt bağlı Blueprint adayını onayladı.",
    )

    row = connection.execute(
        "SELECT * FROM product_blueprint WHERE id=?", (blueprint_id,)
    ).fetchone()
    evidence = connection.execute(
        "SELECT statement_text,claim_id FROM blueprint_evidence WHERE blueprint_id=?",
        (blueprint_id,),
    ).fetchone()
    decision = connection.execute(
        "SELECT actor,action,rationale FROM decision_log WHERE entity_id=?",
        (blueprint_id,),
    ).fetchone()
    assert row["opportunity_id"] == opportunity_id
    assert row["status"] == "APPROVED"
    assert row["approved_by"] == "human:serhat"
    assert tuple(evidence) == ("Observed price signal", claim_id)
    assert tuple(decision) == (
        "human:serhat", "APPROVE", "Kullanıcı kanıt bağlı Blueprint adayını onayladı."
    )


def test_s4_t11_reapproving_same_candidate_is_idempotent(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "repeat"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )
    kwargs = dict(
        approved=True,
        actor="human:serhat",
        rationale="Kullanıcı Blueprint adayını onayladı.",
    )

    first = apply_blueprint_decision(connection, proposal, **kwargs)
    second = apply_blueprint_decision(connection, proposal, **kwargs)

    assert second == first
    assert connection.execute("SELECT COUNT(*) FROM product_blueprint").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM blueprint_evidence").fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM decision_log WHERE entity_id=?", (first,)
    ).fetchone()[0] == 1


def test_s4_t12_blueprint_approval_does_not_mutate_source_claim_or_snapshot(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "immutable"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )
    source_before = dict(connection.execute("SELECT * FROM source").fetchone())
    claim_before = dict(
        connection.execute("SELECT * FROM claim WHERE id=?", (claim_id,)).fetchone()
    )
    snapshot = (tmp_path / "evidence-immutable") / source_before["snapshot_path"]
    snapshot_before = snapshot.read_bytes()

    apply_blueprint_decision(
        connection,
        proposal,
        approved=True,
        rationale="Kullanıcı değişmez kanıt bağlı Blueprint'i onayladı.",
    )

    assert dict(connection.execute("SELECT * FROM source").fetchone()) == source_before
    assert dict(
        connection.execute("SELECT * FROM claim WHERE id=?", (claim_id,)).fetchone()
    ) == claim_before
    assert snapshot.read_bytes() == snapshot_before


def test_s4_t13_blueprint_has_no_kdp_or_publication_side_effect(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "publish-safe"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )

    apply_blueprint_decision(
        connection,
        proposal,
        approved=True,
        rationale="Kullanıcı yalnız Product Blueprint'i onayladı.",
    )

    assert connection.execute(
        "SELECT status FROM opportunity WHERE id=?", (opportunity_id,)
    ).fetchone()[0] == "APPROVED"
    publication_tables = connection.execute(
        """SELECT name FROM sqlite_master WHERE type='table'
           AND (lower(name) LIKE '%kdp%' OR lower(name) LIKE '%publication%')"""
    ).fetchall()
    assert publication_tables == []


def test_s4_t14_report_shows_every_evidence_claim_link(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "report"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(
            EvidenceStatement("Observed price signal", (claim_id,)),
            EvidenceStatement("Price informs positioning", (claim_id,)),
        ),
    )
    blueprint_id = apply_blueprint_decision(
        connection,
        proposal,
        approved=True,
        rationale="Kullanıcı raporlanacak Blueprint'i onayladı.",
    )

    report = generate_blueprint_report(
        connection,
        blueprint_id=blueprint_id,
        out_path=tmp_path / "blueprint.html",
    ).read_text(encoding="utf-8")

    assert "Observed price signal" in report
    assert "Price informs positioning" in report
    assert report.count(f"[{claim_id}]") == 2
    assert "Conversion rate" in report


def test_s4_t15_blueprint_preserves_zero_unbound_claims(connection, tmp_path):
    opportunity_id, claim_id = approved_opportunity_with_claim(
        connection, tmp_path, "final"
    )
    proposal = replace(
        candidate(opportunity_id),
        evidence_claim_ids=(claim_id,),
        evidence_statements=(EvidenceStatement("Observed price signal", (claim_id,)),),
    )

    apply_blueprint_decision(
        connection,
        proposal,
        approved=True,
        rationale="Kullanıcı acceptance Blueprint'ini onayladı.",
    )

    assert connection.execute(
        "SELECT COUNT(*) FROM claim WHERE opportunity_id IS NULL"
    ).fetchone()[0] == 0
    assert connection.execute(
        """SELECT COUNT(*) FROM blueprint_evidence be
           LEFT JOIN claim c ON c.id=be.claim_id WHERE c.id IS NULL"""
    ).fetchone()[0] == 0
