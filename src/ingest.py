from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import EVIDENCE_DIR, isoformat_utc, utc_now
from .hashing import sha256_bytes
from .ids import next_id
from .secrets_scan import scan_for_secrets
from .snapshot import write_snapshot
from .vocab import SOURCE_KINDS, require_source_family


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    duplicate: bool
    message: str


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def infer_content_type(file_name: str | None, kind: str) -> str:
    if kind == "MANUAL_SCREENSHOT":
        return "image/png"
    suffix = Path(file_name or "").suffix.lower()
    return {".csv": "text/csv", ".html": "text/html", ".htm": "text/html"}.get(suffix, "text/plain")


def ingest(
    connection,
    *,
    data: bytes,
    source_family: str,
    kind: str,
    retrieved_at: str,
    url: str | None,
    evidence_dir: Path = EVIDENCE_DIR,
    locale: str = "US",
    collector: str = "human:serhat",
    file_name: str | None = None,
    reliability_override: str | None = None,
    override_rationale: str | None = None,
    note: str | None = None,
) -> IngestResult:
    if not data:
        raise ValueError("Ham içerik boş olamaz")
    if kind not in SOURCE_KINDS:
        raise ValueError(f"Geçersiz source kind: {kind}")
    if kind in {"MANUAL_PASTE", "MANUAL_FILE"} and not url:
        raise ValueError("Metin tabanlı manuel kaynaklarda URL zorunludur")
    reliability, legal_status = require_source_family(source_family)
    if reliability_override:
        if not override_rationale:
            raise ValueError("Reliability override için gerekçe zorunludur")
        reliability = reliability_override
    retrieved = _parse_time(retrieved_at)
    now = utc_now()
    if retrieved > now:
        raise ValueError("retrieved_at gelecekte olamaz")
    content_type = infer_content_type(file_name, kind)
    if content_type.startswith("text/"):
        scan_for_secrets(data)
    raw_hash = sha256_bytes(data)
    existing = connection.execute(
        "SELECT * FROM source WHERE raw_hash=?", (raw_hash,)
    ).fetchone()
    if existing:
        return IngestResult(
            existing["id"], True,
            f"Bu içerik zaten {existing['id']} olarak kayıtlı (ilk gözlem: {existing['retrieved_at']})",
        )
    source_id = next_id(connection, "source")
    ingested_at = isoformat_utc(now)
    meta = {
        "source_id": source_id, "source_family": source_family, "kind": kind,
        "url": url, "locale": locale, "retrieved_at": retrieved.replace(microsecond=0).isoformat(),
        "ingested_at": ingested_at, "raw_hash": raw_hash, "content_type": content_type,
        "byte_size": len(data), "collector": collector,
    }
    relative = write_snapshot(evidence_dir, data, meta)
    with connection:
        connection.execute(
            """INSERT INTO source(id,kind,source_family,url,locale,retrieved_at,ingested_at,
            raw_hash,snapshot_path,content_type,byte_size,legal_status,reliability,ttl_days,
            collector,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id, kind, source_family, url, locale, meta["retrieved_at"], ingested_at,
             raw_hash, str(relative), content_type, len(data), legal_status, reliability, 0,
             collector, note),
        )
    return IngestResult(source_id, False, source_id)
