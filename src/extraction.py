from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import json
from pathlib import Path
from typing import Protocol

from .claims import ClaimResult, _numeric_in_quote, _time, add_claim
from .config import EVIDENCE_DIR
from .cost import LLMDisabledError
from .snapshot import verify_snapshots
from .vocab import CONFIDENCE_BY_RELIABILITY, require_claim_type, unit_is_valid


@dataclass(frozen=True)
class ClaimCandidate:
    source_id: str
    claim_type: str
    subject: str
    observed_at: str
    value_num: float | None = None
    value_text: str | None = None
    unit: str | None = None
    market: str | None = None
    confidence: str | None = None
    quote: str | None = None
    locator: str | None = None


class ClaimExtractor(Protocol):
    def extract(self, request: object) -> object: ...


@dataclass(frozen=True)
class DeterministicDryRunExtractor:
    """Network-free extractor used to exercise the human review flow."""

    output: str

    def extract(self, request: object) -> str:
        return self.output


def render_candidate_review(candidates: list[ClaimCandidate]) -> str:
    """Render proposals for human review without changing persistent state."""
    lines = ["S-3 CLAIM ADAYLARI — İNSAN ONAYI GEREKİR"]
    if not candidates:
        return "\n".join([*lines, "Aday bulunamadı."])
    for index, candidate in enumerate(candidates, 1):
        value = candidate.value_num if candidate.value_num is not None else candidate.value_text
        rendered_value = f"{value} {candidate.unit}" if candidate.unit else str(value)
        evidence = candidate.quote or candidate.locator or "KANIT KONUMU YOK"
        lines.extend(
            [
                "",
                f"[{index}] {candidate.claim_type}",
                f"Kaynak: {candidate.source_id}",
                f"Konu: {candidate.subject}",
                f"Değer: {rendered_value}",
                f"Kanıt: {evidence}",
                "Karar: BEKLİYOR — ONAY veya RED zorunlu",
            ]
        )
    return "\n".join(lines)


def apply_candidate_decision(
    connection,
    candidate: ClaimCandidate,
    *,
    approved: bool,
    extracted_by: str,
    evidence_dir: Path = EVIDENCE_DIR,
    opportunity_id: str | None = None,
) -> ClaimResult | None:
    """Persist only an explicitly human-approved, revalidated candidate."""
    if not approved:
        return None
    validated = validate_claim_candidate(connection, candidate, evidence_dir=evidence_dir)
    existing = connection.execute(
        """SELECT id, confidence FROM claim
           WHERE source_id=? AND claim_type=? AND subject=? AND observed_at=?""",
        (
            validated.source_id,
            validated.claim_type,
            validated.subject,
            validated.observed_at,
        ),
    ).fetchone()
    if existing:
        return ClaimResult(
            existing["id"], existing["confidence"], "Aday daha önce claim olarak kaydedilmiş"
        )
    return add_claim(
        connection,
        source_id=validated.source_id,
        claim_type=validated.claim_type,
        subject=validated.subject,
        observed_at=validated.observed_at,
        value_num=validated.value_num,
        value_text=validated.value_text,
        unit=validated.unit,
        market=validated.market,
        confidence=validated.confidence,
        extracted_by=extracted_by,
        quote=validated.quote,
        locator=validated.locator,
        opportunity_id=opportunity_id,
        evidence_dir=evidence_dir,
    )


def validate_claim_candidate(
    connection,
    candidate: ClaimCandidate,
    *,
    evidence_dir: Path = EVIDENCE_DIR,
) -> ClaimCandidate:
    """Validate an extraction proposal without writing a claim."""
    source = connection.execute(
        "SELECT * FROM source WHERE id=?", (candidate.source_id,)
    ).fetchone()
    if source is None:
        raise ValueError("S3-CB-1: source_id mevcut bir kaynağa bağlanmalıdır")
    spec = require_claim_type(candidate.claim_type)
    if not candidate.subject.strip():
        raise ValueError("subject zorunludur")
    if spec.value_kind == "num":
        if candidate.value_num is None or not unit_is_valid(spec, candidate.unit):
            raise ValueError("S3-CB-2: sayısal değer ve geçerli birim zorunludur")
    elif candidate.value_text is None:
        raise ValueError("Metinsel değer zorunludur")
    if len(candidate.observed_at) == 10:
        observed_is_future = (
            date.fromisoformat(candidate.observed_at) > _time(source["retrieved_at"]).date()
        )
    else:
        observed_is_future = _time(candidate.observed_at) > _time(source["retrieved_at"])
    if observed_is_future:
        raise ValueError("S3-CB-3: observed_at source.retrieved_at değerini aşamaz")
    if candidate.source_id in verify_snapshots(connection, evidence_dir):
        raise ValueError("S3-CB-5: snapshot eksik veya hash uyuşmuyor")
    if source["content_type"].startswith("text/"):
        if not candidate.quote:
            raise ValueError("S3-CB-4: exact quote zorunludur")
        if len(candidate.quote) > 200:
            raise ValueError("S3-CB-4: quote en fazla 200 karakter olabilir")
        if spec.value_kind == "num":
            if len(candidate.quote) < 12:
                raise ValueError("S3-CB-4: sayısal quote en az 12 karakterlik bağlam içermelidir")
            if not _numeric_in_quote(float(candidate.value_num), candidate.quote):
                raise ValueError("S3-CB-4: value_num quote içinde bulunmalıdır")
        snapshot = (evidence_dir / source["snapshot_path"]).read_text(encoding="utf-8")
        if candidate.quote not in snapshot:
            raise ValueError("S3-CB-4: quote snapshot içinde birebir bulunmalıdır")
    elif source["content_type"].startswith("image/"):
        if not candidate.locator or not candidate.locator.strip():
            raise ValueError("S3-CB-4: ekran görüntüsü için locator zorunludur")
        confidence = candidate.confidence or CONFIDENCE_BY_RELIABILITY[source["reliability"]]
        if confidence == "HIGH":
            confidence = "MEDIUM"
        return replace(candidate, confidence=confidence)
    return candidate


def run_claim_extraction(
    connection,
    *,
    source_id: str,
    extractor: ClaimExtractor,
    llm_enabled: bool = False,
    evidence_dir: Path = EVIDENCE_DIR,
):
    """Return validated proposals; never persist model output as claims."""
    if not llm_enabled and not isinstance(extractor, DeterministicDryRunExtractor):
        raise LLMDisabledError("S-3 LLM bütçesi kapalıdır")
    proposals = extractor.extract({"source_id": source_id})
    if isinstance(proposals, str):
        try:
            proposals = json.loads(proposals)
        except json.JSONDecodeError as exc:
            raise ValueError("S-3 çıkarıcı çıktısı geçerli JSON değildir") from exc
    if not isinstance(proposals, list):
        raise ValueError("S-3 çıkarıcı çıktısı bir aday listesi olmalıdır")
    validated: list[ClaimCandidate] = []
    for proposal in proposals:
        if isinstance(proposal, dict):
            try:
                proposal = ClaimCandidate(**proposal)
            except TypeError as exc:
                raise ValueError("S-3 claim adayı şeması eksik veya geçersiz") from exc
        if not isinstance(proposal, ClaimCandidate):
            raise ValueError("S-3 çıkarıcı çıktısı geçersiz claim adayı içeriyor")
        if proposal.source_id != source_id:
            raise ValueError("S3-CB-1: aday istenen source_id ile eşleşmelidir")
        validated.append(
            validate_claim_candidate(connection, proposal, evidence_dir=evidence_dir)
        )
    return validated
