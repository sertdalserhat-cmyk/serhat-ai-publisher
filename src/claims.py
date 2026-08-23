from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .config import EVIDENCE_DIR, isoformat_utc, utc_now
from .ids import next_id
from .snapshot import verify_snapshots
from .vocab import CONFIDENCE_BY_RELIABILITY, require_claim_type


@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    confidence: str
    warning: str | None = None


def _time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.combine(date.fromisoformat(value), datetime.min.time())
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _numeric_in_quote(value: float, quote: str) -> bool:
    if float(value).is_integer():
        expected = str(int(value))
        compact = re.sub(r"(?<=\d)[,\.\s\u202f](?=\d{3}(?:\D|$))", "", quote)
        return expected in re.sub(r"[^0-9]", "", compact)
    expected = format(value, "g")
    cleaned = quote.replace("\u202f", " ").replace(" ", "").replace(",", ".")
    return expected in re.sub(r"[^0-9.]", "", cleaned)


def add_claim(
    connection,
    *,
    source_id: str | None,
    claim_type: str,
    subject: str,
    observed_at: str,
    value_num: float | None = None,
    value_text: str | None = None,
    unit: str | None = None,
    market: str | None = None,
    confidence: str | None = None,
    extracted_by: str = "human:serhat",
    quote: str | None = None,
    locator: str | None = None,
    opportunity_id: str | None = None,
    evidence_dir: Path = EVIDENCE_DIR,
) -> ClaimResult:
    if not source_id:
        raise ValueError("CB-1: source_id zorunludur")
    spec = require_claim_type(claim_type)
    source = connection.execute("SELECT * FROM source WHERE id=?", (source_id,)).fetchone()
    if source is None:
        raise sqlite3.IntegrityError("FOREIGN KEY constraint failed: source_id")
    if not subject.strip():
        raise ValueError("subject zorunludur")
    if spec.value_kind == "num":
        if value_num is None or unit is None:
            raise ValueError("CB-2: sayısal iddia için value_num ve unit zorunludur")
        if unit != spec.unit:
            raise ValueError(f"CB-2: unit {spec.unit!r} olmalıdır")
    elif value_text is None:
        raise ValueError("Metinsel iddia için value_text zorunludur")
    if len(observed_at) == 10:
        observed_is_future = date.fromisoformat(observed_at) > _time(source["retrieved_at"]).date()
    else:
        observed_is_future = _time(observed_at) > _time(source["retrieved_at"])
    if observed_is_future:
        raise ValueError("CB-3: observed_at source.retrieved_at değerini aşamaz")
    damaged = verify_snapshots(connection, evidence_dir)
    if source_id in damaged:
        raise ValueError("CB-5: snapshot eksik veya hash uyuşmuyor")
    chosen_confidence = confidence or CONFIDENCE_BY_RELIABILITY[source["reliability"]]
    warning = None
    if source["content_type"].startswith("text/"):
        if not quote:
            raise ValueError("CB-4: quote zorunludur")
        if len(quote) > 200:
            raise ValueError("CB-4: quote en fazla 200 karakter olabilir")
        if spec.value_kind == "num":
            if len(quote) < 12:
                raise ValueError("CB-4: sayısal quote en az 12 karakterlik bağlam içermelidir")
            if not _numeric_in_quote(float(value_num), quote):
                raise ValueError("CB-4: value_num quote içinde bulunmalıdır")
        if (evidence_dir / source["snapshot_path"]).read_text(encoding="utf-8").find(quote) < 0:
            raise ValueError("CB-4: quote snapshot içinde birebir bulunmalıdır")
    elif source["content_type"].startswith("image/"):
        if not locator or not locator.strip():
            raise ValueError("CB-4: ekran görüntüsü için locator zorunludur")
        if chosen_confidence == "HIGH":
            chosen_confidence = "MEDIUM"
            warning = "Ekran görüntüsü kaynağı: confidence MEDIUM'a indirildi"
    claim_id = next_id(connection, "claim")
    try:
        with connection:
            connection.execute(
                """INSERT INTO claim(id,source_id,opportunity_id,claim_type,subject,value_num,
                value_text,unit,market,observed_at,confidence,extracted_by,quote,locator,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (claim_id, source_id, opportunity_id, claim_type, subject, value_num, value_text,
                 unit, market, observed_at, chosen_confidence, extracted_by, quote, locator,
                 isoformat_utc(utc_now())),
            )
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc):
            raise ValueError("Bu claim zaten kayıtlı") from exc
        raise
    return ClaimResult(claim_id, chosen_confidence, warning)
