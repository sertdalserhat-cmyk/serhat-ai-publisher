class LLMDisabledError(RuntimeError):
    pass


def record_llm_call(connection, *args, llm_enabled=False, **kwargs):
    if not llm_enabled:
        raise LLMDisabledError("S-2 aşamasında LLM çağrıları kapalıdır")
    raise LLMDisabledError("S-2 hiçbir LLM çağrısını uygulamaz")
