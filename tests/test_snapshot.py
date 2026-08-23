from __future__ import annotations

import os

from src.hashing import sha256_bytes
from src.snapshot import verify_snapshots, write_snapshot


def _source_meta(data: bytes) -> dict[str, object]:
    return {
        "source_id": "src_000001",
        "source_family": "AMAZON_KDP",
        "kind": "MANUAL_FILE",
        "url": "https://example.test/source",
        "locale": "US",
        "retrieved_at": "2026-08-23T14:10:00+00:00",
        "ingested_at": "2026-08-23T14:11:00+00:00",
        "raw_hash": sha256_bytes(data),
        "content_type": "text/plain",
        "byte_size": len(data),
        "collector": "human:serhat",
    }


def _insert_source(connection, meta, relative):
    connection.execute(
        """INSERT INTO source(id,kind,source_family,url,locale,retrieved_at,ingested_at,
        raw_hash,snapshot_path,content_type,byte_size,legal_status,reliability,ttl_days,
        collector) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (meta["source_id"], meta["kind"], meta["source_family"], meta["url"],
         meta["locale"], meta["retrieved_at"], meta["ingested_at"], meta["raw_hash"],
         str(relative), meta["content_type"], meta["byte_size"], "PUBLIC_MANUAL", "B", 7,
         meta["collector"]),
    )
    connection.commit()


def test_t02_snapshot_hash_and_read_only(connection, tmp_path):
    data = b"1,234 results for nursery wall art"
    meta = _source_meta(data)
    evidence = tmp_path / "evidence"
    relative = write_snapshot(evidence, data, meta)
    _insert_source(connection, meta, relative)
    path = evidence / relative
    assert sha256_bytes(path.read_bytes()) == meta["raw_hash"]
    assert os.stat(path).st_mode & 0o222 == 0
    assert len(list(evidence.rglob("*.txt"))) == 1
    assert verify_snapshots(connection, evidence) == []


def test_t11_verify_reports_tampered_source(connection, tmp_path):
    data = b"original evidence"
    meta = _source_meta(data)
    evidence = tmp_path / "evidence"
    relative = write_snapshot(evidence, data, meta)
    _insert_source(connection, meta, relative)
    path = evidence / relative
    os.chmod(path, 0o644)
    path.write_bytes(b"tampered")
    assert verify_snapshots(connection, evidence) == ["src_000001"]


def test_t03_duplicate_ingest_returns_same_id_without_mutation(connection, tmp_path):
    from src.ingest import ingest

    evidence = tmp_path / "evidence"
    args = dict(
        data=b"duplicate evidence bytes",
        source_family="AMAZON_KDP",
        kind="MANUAL_PASTE",
        url="https://example.test/search",
        retrieved_at="2026-08-23T14:10:00+00:00",
        evidence_dir=evidence,
    )
    first = ingest(connection, **args)
    before = tuple(connection.execute("SELECT * FROM source WHERE id=?", (first.source_id,)).fetchone())
    second = ingest(connection, **args)
    after = tuple(connection.execute("SELECT * FROM source WHERE id=?", (first.source_id,)).fetchone())
    assert second.source_id == first.source_id
    assert second.duplicate is True
    assert "zaten" in second.message
    assert before == after
    assert connection.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 1
