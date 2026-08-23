import pytest

from src.cost import LLMDisabledError, record_llm_call


def test_t14_llm_guard_rejects_without_log(connection):
    with pytest.raises(LLMDisabledError):
        record_llm_call(connection, llm_enabled=False)
    assert connection.execute("SELECT COUNT(*) FROM llm_call").fetchone()[0] == 0
