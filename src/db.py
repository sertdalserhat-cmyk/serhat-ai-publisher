from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from .config import DB_PATH, isoformat_utc, utc_now


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(path: Path | str = DB_PATH) -> sqlite3.Connection:
    connection = connect(path)
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    with connection:
        connection.execute(
            """INSERT INTO meta(key, value) VALUES('schema_version', '3')
               ON CONFLICT(key) DO UPDATE SET value='3'"""
        )
        connection.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('created_at', ?)",
            (isoformat_utc(utc_now()),),
        )
        connection.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('db_uuid', ?)",
            (str(uuid.uuid4()),),
        )
    return connection
