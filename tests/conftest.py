from __future__ import annotations

from pathlib import Path

import pytest

from src.db import initialize


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "publisher.db"


@pytest.fixture
def connection(db_path: Path):
    conn = initialize(db_path)
    try:
        yield conn
    finally:
        conn.close()
