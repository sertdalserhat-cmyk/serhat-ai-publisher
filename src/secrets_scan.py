from __future__ import annotations


SECRET_LITERALS = (
    "sk-", "sk-ant-", "AKIA", "ASIA", "ghp_", "-----BEGIN",
    "Bearer", "AIza", "xoxb-", "password=", "api_key=",
)


class SecretDetectedError(ValueError):
    pass


def scan_for_secrets(data: bytes) -> None:
    text = data.decode("utf-8", errors="replace")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for literal in SECRET_LITERALS:
            if literal in line:
                raise SecretDetectedError(
                    f"Olası gizli bilgi: satır {line_number}, desen {literal!r}"
                )
