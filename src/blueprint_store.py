from __future__ import annotations

import sqlite3

from .config import isoformat_utc, utc_now
from .decisions import log_decision


REQUIRED_TEXT = (
    "audience", "customer_problem", "product_promise",
    "differentiator", "currency", "content_structure",
)


def load_blueprint(conn: sqlite3.Connection, opportunity_id: str):
    return conn.execute(
        "SELECT * FROM product_blueprint WHERE opportunity_id=?", (opportunity_id,)
    ).fetchone()


def save_blueprint(conn: sqlite3.Connection, opportunity_id: str, data: dict[str, object]) -> int:
    opportunity = conn.execute(
        "SELECT status FROM opportunity WHERE id=?", (opportunity_id,)
    ).fetchone()
    if not opportunity:
        raise ValueError("Fırsat bulunamadı")
    if opportunity["status"] != "APPROVED":
        raise ValueError("Blueprint yalnız APPROVED fırsat için kaydedilebilir")
    for field in REQUIRED_TEXT:
        if not str(data.get(field, "")).strip():
            raise ValueError(f"Zorunlu alan: {field}")
    try:
        age_min, age_max = int(data["age_min"]), int(data["age_max"])
        page_count, activity_count = int(data["page_count"]), int(data["activity_count"])
        target_price = float(data["target_price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Sayısal Blueprint alanları geçersiz") from exc
    if age_min < 0 or age_max < age_min or page_count < 1 or activity_count < 1 or target_price <= 0:
        raise ValueError("Blueprint sayı aralıkları geçersiz")
    now = isoformat_utc(utc_now())
    current = conn.execute(
        "SELECT version,created_at FROM product_blueprint WHERE opportunity_id=?",
        (opportunity_id,),
    ).fetchone()
    version = (current["version"] + 1) if current else 1
    created_at = current["created_at"] if current else now
    values = (
        opportunity_id, *(str(data[x]).strip() for x in REQUIRED_TEXT[:3]),
        age_min, age_max, page_count, activity_count,
        str(data["differentiator"]).strip(), target_price,
        str(data["currency"]).strip().upper(), str(data["content_structure"]).strip(),
        version, created_at, now,
    )
    with conn:
        conn.execute("""INSERT INTO product_blueprint
          (opportunity_id,audience,customer_problem,product_promise,age_min,age_max,
           page_count,activity_count,differentiator,target_price,currency,
           content_structure,version,created_at,updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(opportunity_id) DO UPDATE SET
           audience=excluded.audience,customer_problem=excluded.customer_problem,
           product_promise=excluded.product_promise,age_min=excluded.age_min,
           age_max=excluded.age_max,page_count=excluded.page_count,
           activity_count=excluded.activity_count,differentiator=excluded.differentiator,
           target_price=excluded.target_price,currency=excluded.currency,
           content_structure=excluded.content_structure,version=excluded.version,
           updated_at=excluded.updated_at""", values)
    log_decision(conn, entity_type="BLUEPRINT", entity_id=opportunity_id,
                 actor="human:serhat", action="SAVE",
                 rationale=f"Kullanıcı Product Blueprint v{version} kaydetti")
    return version
