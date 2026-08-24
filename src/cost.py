from __future__ import annotations

from .config import isoformat_utc, utc_now
from .ids import next_id


class LLMDisabledError(RuntimeError):
    pass


def record_llm_call(connection, *args, llm_enabled=False, **kwargs):
    if not llm_enabled:
        raise LLMDisabledError("S-2 aşamasında LLM çağrıları kapalıdır")
    required = {
        "task_key", "model", "in_tokens", "out_tokens", "cost_usd",
        "pricing_ver", "schema_valid", "input_hash",
    }
    missing = sorted(required.difference(kwargs))
    if missing:
        raise ValueError(f"LLM denetim kaydı eksik alanlar: {', '.join(missing)}")
    if kwargs["in_tokens"] < 0 or kwargs["out_tokens"] < 0 or kwargs["cost_usd"] < 0:
        raise ValueError("Token ve maliyet değerleri negatif olamaz")
    call_id = next_id(connection, "llm_call")
    with connection:
        connection.execute(
            """INSERT INTO llm_call(
                id,task_key,model,in_tokens,out_tokens,cost_usd,pricing_ver,
                schema_valid,retry_count,input_hash,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                call_id, kwargs["task_key"], kwargs["model"], kwargs["in_tokens"],
                kwargs["out_tokens"], kwargs["cost_usd"], kwargs["pricing_ver"],
                int(bool(kwargs["schema_valid"])), kwargs.get("retry_count", 0),
                kwargs["input_hash"], isoformat_utc(utc_now()),
            ),
        )
    return call_id
