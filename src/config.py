from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_DIR = ROOT_DIR / "db"
DB_PATH = DB_DIR / "publisher.db"
EVIDENCE_DIR = ROOT_DIR / "evidence"
BACKUP_DIR = DB_DIR / "backups"

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
