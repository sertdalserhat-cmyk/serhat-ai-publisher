from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from .hashing import sha256_bytes


EXTENSIONS = {
    "text/plain": ".txt",
    "text/csv": ".csv",
    "text/html": ".html",
    "image/png": ".png",
}


def snapshot_relative_path(meta: Mapping[str, object]) -> Path:
    retrieved = str(meta["retrieved_at"])
    return Path(retrieved[:4], retrieved[5:7], str(meta["source_family"]), str(meta["raw_hash"])[:32] + EXTENSIONS[str(meta["content_type"])])


def write_snapshot(evidence_dir: Path, data: bytes, meta: Mapping[str, object]) -> Path:
    relative = snapshot_relative_path(meta)
    target = evidence_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Snapshot zaten mevcut: {relative}")
    target.write_bytes(data)
    meta_path = target.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(dict(meta), ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(target, 0o444)
    os.chmod(meta_path, 0o444)
    return relative


def read_snapshot(evidence_dir: Path, relative_path: str | Path) -> bytes:
    return (evidence_dir / relative_path).read_bytes()


def verify_snapshots(connection, evidence_dir: Path) -> list[str]:
    damaged: list[str] = []
    for row in connection.execute("SELECT id, raw_hash, snapshot_path FROM source"):
        path = evidence_dir / row["snapshot_path"]
        if not path.exists() or sha256_bytes(path.read_bytes()) != row["raw_hash"]:
            damaged.append(row["id"])
    return damaged
