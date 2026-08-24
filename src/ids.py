from __future__ import annotations

import sqlite3


PREFIX_WIDTHS = {
    "source": ("src", 6),
    "claim": ("clm", 6),
    "opportunity": ("opp", 4),
    "decision_log": ("dec", 6),
    "llm_call": ("llm", 6),
    "bot_run": ("run", 6),
    "bot_task": ("tsk", 6),
}


def next_id(connection: sqlite3.Connection, table: str) -> str:
    try:
        prefix, width = PREFIX_WIDTHS[table]
    except KeyError as exc:
        raise ValueError(f"Bilinmeyen kimlik tablosu: {table}") from exc
    rows = connection.execute(f"SELECT id FROM {table}").fetchall()
    highest = 0
    marker = f"{prefix}_"
    for row in rows:
        value = row[0]
        if value.startswith(marker) and value[len(marker):].isdigit():
            highest = max(highest, int(value[len(marker):]))
    return f"{prefix}_{highest + 1:0{width}d}"
