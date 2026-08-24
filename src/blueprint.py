from __future__ import annotations

from dataclasses import dataclass
import html
import json
from pathlib import Path
from typing import Protocol

from .config import isoformat_utc, utc_now
from .cost import LLMDisabledError
from .decisions import log_decision
from .ids import next_id


@dataclass(frozen=True)
class EvidenceStatement:
    text: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class BlueprintCandidate:
    opportunity_id: str
    working_title: str
    target_reader: str
    reader_problem: str
    product_promise: str
    format: str
    language: str
    market: str
    differentiators: tuple[str, ...]
    content_outline: tuple[str, ...]
    risks: tuple[str, ...]
    unknowns: tuple[str, ...]
    evidence_claim_ids: tuple[str, ...]
    evidence_statements: tuple[EvidenceStatement, ...]
    status: str = "DRAFT_REVIEW"


class BlueprintExtractor(Protocol):
    def generate(self, request: object) -> BlueprintCandidate: ...


@dataclass(frozen=True)
class DeterministicBlueprintExtractor:
    candidate: BlueprintCandidate

    def generate(self, request: object) -> BlueprintCandidate:
        return self.candidate


def run_blueprint_generation(
    connection,
    *,
    opportunity_id: str,
    extractor: BlueprintExtractor,
    llm_enabled: bool = False,
) -> BlueprintCandidate:
    if not llm_enabled and not isinstance(extractor, DeterministicBlueprintExtractor):
        raise LLMDisabledError("S-4 LLM bütçesi kapalıdır")
    proposal = extractor.generate({"opportunity_id": opportunity_id})
    if not isinstance(proposal, BlueprintCandidate):
        raise ValueError("S-4 çıkarıcı çıktısı geçerli Blueprint adayı değildir")
    if proposal.opportunity_id != opportunity_id:
        raise ValueError("S-4 Blueprint adayı istenen fırsatla eşleşmiyor")
    return validate_blueprint_candidate(connection, proposal)


def apply_blueprint_decision(
    connection,
    candidate: BlueprintCandidate,
    *,
    approved: bool,
    actor: str = "human:serhat",
    rationale: str | None = None,
):
    if not approved:
        return None
    if not rationale or not rationale.strip():
        raise ValueError("S4-T10: Blueprint onayı için gerekçe zorunludur")
    validated = validate_blueprint_candidate(connection, candidate)
    existing = connection.execute(
        "SELECT id FROM product_blueprint WHERE opportunity_id=?",
        (validated.opportunity_id,),
    ).fetchone()
    if existing:
        return existing["id"]
    blueprint_id = next_id(connection, "product_blueprint")
    now = isoformat_utc(utc_now())
    with connection:
        connection.execute(
            """INSERT INTO product_blueprint(
                id,opportunity_id,working_title,target_reader,reader_problem,
                product_promise,format,language,market,differentiators,
                content_outline,risks,unknowns,status,approved_by,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                blueprint_id, validated.opportunity_id, validated.working_title,
                validated.target_reader, validated.reader_problem,
                validated.product_promise, validated.format, validated.language,
                validated.market, json.dumps(validated.differentiators, ensure_ascii=False),
                json.dumps(validated.content_outline, ensure_ascii=False),
                json.dumps(validated.risks, ensure_ascii=False),
                json.dumps(validated.unknowns, ensure_ascii=False),
                "APPROVED", actor, now,
            ),
        )
        for statement_no, statement in enumerate(validated.evidence_statements, 1):
            for claim_id in statement.claim_ids:
                connection.execute(
                    """INSERT INTO blueprint_evidence(
                        blueprint_id,statement_no,statement_text,claim_id
                    ) VALUES(?,?,?,?)""",
                    (blueprint_id, statement_no, statement.text, claim_id),
                )
    log_decision(
        connection,
        entity_type="PRODUCT_BLUEPRINT",
        entity_id=blueprint_id,
        actor=actor,
        action="APPROVE",
        rationale=rationale,
    )
    return blueprint_id


def generate_blueprint_report(connection, *, blueprint_id: str, out_path: Path | str) -> Path:
    blueprint = connection.execute(
        "SELECT * FROM product_blueprint WHERE id=?", (blueprint_id,)
    ).fetchone()
    if blueprint is None:
        raise ValueError("Product Blueprint bulunamadı")
    evidence = connection.execute(
        """SELECT statement_no,statement_text,claim_id
           FROM blueprint_evidence WHERE blueprint_id=?
           ORDER BY statement_no,claim_id""",
        (blueprint_id,),
    ).fetchall()
    items = "".join(
        f"<li>{html.escape(row['statement_text'])} "
        f"<strong>[{html.escape(row['claim_id'])}]</strong></li>"
        for row in evidence
    )
    unknowns = "".join(
        f"<li>{html.escape(item)}</li>" for item in json.loads(blueprint["unknowns"])
    )
    body = (
        "<!doctype html><html lang='tr'><meta charset='utf-8'>"
        f"<title>{html.escape(blueprint['working_title'])}</title><body>"
        f"<h1>{html.escape(blueprint['working_title'])}</h1>"
        f"<p>Fırsat: {html.escape(blueprint['opportunity_id'])}</p>"
        f"<h2>Kanıt bağlantıları</h2><ul>{items}</ul>"
        f"<h2>UNKNOWN</h2><ul>{unknowns}</ul></body></html>"
    )
    path = Path(out_path)
    path.write_text(body, encoding="utf-8")
    return path


def validate_blueprint_candidate(connection, candidate: BlueprintCandidate) -> BlueprintCandidate:
    opportunity = connection.execute(
        "SELECT id,status FROM opportunity WHERE id=?", (candidate.opportunity_id,)
    ).fetchone()
    if opportunity is None:
        raise ValueError("S4-T01: fırsat bulunamadı")
    if opportunity["status"] != "APPROVED":
        raise ValueError("S4-T01: Product Blueprint için fırsat APPROVED olmalıdır")
    required_text = {
        "working_title": candidate.working_title,
        "target_reader": candidate.target_reader,
        "reader_problem": candidate.reader_problem,
        "product_promise": candidate.product_promise,
        "format": candidate.format,
        "language": candidate.language,
        "market": candidate.market,
    }
    missing = [name for name, value in required_text.items() if not value.strip()]
    if missing or candidate.status != "DRAFT_REVIEW":
        details = ", ".join(missing) if missing else "status"
        raise ValueError(f"S4-T05: zorunlu Blueprint alanı eksik/geçersiz: {details}")
    if not candidate.unknowns or any(not item.strip() for item in candidate.unknowns):
        raise ValueError("S4-T06: kanıtlanmayan alanlar UNKNOWN olarak korunmalıdır")
    active_claims = connection.execute(
        "SELECT COUNT(*) FROM claim WHERE opportunity_id=? AND status='ACTIVE'",
        (candidate.opportunity_id,),
    ).fetchone()[0]
    if active_claims == 0:
        raise ValueError("S4-T02: Blueprint için en az bir bağlı aktif claim zorunludur")
    allowed_claim_ids = {
        row["id"]
        for row in connection.execute(
            "SELECT id FROM claim WHERE opportunity_id=? AND status='ACTIVE'",
            (candidate.opportunity_id,),
        )
    }
    cited_claim_ids = set(candidate.evidence_claim_ids)
    if not cited_claim_ids or not cited_claim_ids.issubset(allowed_claim_ids):
        raise ValueError("S4-T03: kanıt claim'i bilinmiyor veya başka fırsata ait")
    if not candidate.evidence_statements:
        raise ValueError("S4-T04: en az bir kanıtlı bulgu zorunludur")
    for statement in candidate.evidence_statements:
        if not statement.text.strip() or not statement.claim_ids:
            raise ValueError("S4-T04: her kanıtlı bulgu claim.id taşımalıdır")
        if not set(statement.claim_ids).issubset(allowed_claim_ids):
            raise ValueError("S4-T04: kanıtlı bulgu geçersiz claim.id içeriyor")
    return candidate
