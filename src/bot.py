from __future__ import annotations

import sqlite3

from .config import isoformat_utc, utc_now
from .ids import next_id


PIPELINE = (
    "VALIDATE_EVIDENCE",
    "HUMAN_OPPORTUNITY_DECISION",
    "PRODUCT_BLUEPRINT",
    "AI_RESEARCH_EXPANSION",
)


def create_run(conn: sqlite3.Connection, opportunity_id: str, mode: str = "DRY_RUN") -> str:
    if mode not in {"DRY_RUN", "MANUAL", "LIVE"}:
        raise ValueError("Geçersiz bot modu")
    if not conn.execute("SELECT 1 FROM opportunity WHERE id=?", (opportunity_id,)).fetchone():
        raise ValueError("Fırsat bulunamadı")
    run_id = next_id(conn, "bot_run")
    now = isoformat_utc(utc_now())
    try:
        with conn:
            conn.execute("INSERT INTO bot_run(id,opportunity_id,mode,status,current_step,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                         (run_id, opportunity_id, mode, "RUNNING", PIPELINE[0], now, now))
            for sequence, task_key in enumerate(PIPELINE, 1):
                conn.execute("INSERT INTO bot_task(id,run_id,sequence_no,task_key,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                             (next_id(conn, "bot_task"), run_id, sequence, task_key, now, now))
    except sqlite3.IntegrityError as exc:
        raise ValueError("Aynı anda yalnız bir açık bot çalışması olabilir") from exc
    return run_id


def advance_run(conn: sqlite3.Connection, run_id: str) -> str:
    run = conn.execute("SELECT * FROM bot_run WHERE id=?", (run_id,)).fetchone()
    if not run:
        raise ValueError("Bot çalışması bulunamadı")
    task = conn.execute("""SELECT * FROM bot_task
        WHERE run_id=? AND status NOT IN ('COMPLETED','SKIPPED')
        ORDER BY sequence_no LIMIT 1""", (run_id,)).fetchone()
    if not task:
        _set_run(conn, run_id, "COMPLETED", None)
        return "COMPLETED"
    opportunity = conn.execute("SELECT status FROM opportunity WHERE id=?", (run["opportunity_id"],)).fetchone()
    blueprint = conn.execute("SELECT 1 FROM product_blueprint WHERE opportunity_id=?", (run["opportunity_id"],)).fetchone()
    key = task["task_key"]
    if key == "VALIDATE_EVIDENCE":
        claims = conn.execute("SELECT COUNT(*) FROM claim WHERE opportunity_id=? AND status='ACTIVE'", (run["opportunity_id"],)).fetchone()[0]
        unbound = conn.execute("SELECT COUNT(*) FROM claim WHERE status='ACTIVE' AND opportunity_id IS NULL").fetchone()[0]
        if claims < 30 or unbound:
            return _block(conn, run_id, task["id"], "Kanıt kapısı geçmedi")
        _complete_task(conn, task["id"], f"claims={claims};unbound={unbound}")
    elif key == "HUMAN_OPPORTUNITY_DECISION":
        if opportunity["status"] != "APPROVED":
            return _wait(conn, run_id, task["id"], "İnsan fırsat kararı bekleniyor")
        _complete_task(conn, task["id"], "status=APPROVED")
    elif key == "PRODUCT_BLUEPRINT":
        if not blueprint:
            return _wait(conn, run_id, task["id"], "İnsan Product Blueprint kaydı bekleniyor")
        _complete_task(conn, task["id"], "blueprint=present")
    else:
        return _block(conn, run_id, task["id"], "LLM bütçesi kapalı; AI araştırması çalıştırılmadı")
    _set_run(conn, run_id, "RUNNING", key)
    return "ADVANCED"


def _complete_task(conn, task_id, checkpoint):
    now = isoformat_utc(utc_now())
    with conn:
        conn.execute("UPDATE bot_task SET status='COMPLETED',checkpoint=?,attempt=attempt+1,updated_at=? WHERE id=?", (checkpoint, now, task_id))


def _set_run(conn, run_id, status, step, error=None):
    with conn:
        conn.execute("UPDATE bot_run SET status=?,current_step=?,last_error=?,updated_at=? WHERE id=?",
                     (status, step, error, isoformat_utc(utc_now()), run_id))
    return status


def _wait(conn, run_id, task_id, reason):
    with conn:
        conn.execute("UPDATE bot_task SET status='WAITING_HUMAN',last_error=?,updated_at=? WHERE id=?", (reason, isoformat_utc(utc_now()), task_id))
    return _set_run(conn, run_id, "WAITING_HUMAN", None, reason)


def _block(conn, run_id, task_id, reason):
    with conn:
        conn.execute("UPDATE bot_task SET status='BLOCKED',last_error=?,updated_at=? WHERE id=?", (reason, isoformat_utc(utc_now()), task_id))
    return _set_run(conn, run_id, "BLOCKED", None, reason)
