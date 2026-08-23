from __future__ import annotations

import hashlib
import re
import unicodedata


STOP_WORDS = {"the", "a", "for", "of", "and", "with", "ve", "için"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    tokens = re.findall(r"[^\W_]+", value, flags=re.UNICODE)
    return " ".join(sorted(token for token in tokens if token not in STOP_WORDS))


def jaccard(left: str, right: str) -> float:
    a = set(normalize_text(left).split())
    b = set(normalize_text(right).split())
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if a | b else 0.0
