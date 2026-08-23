from __future__ import annotations

import sqlite3

from .config import isoformat_utc, utc_now
from .decisions import log_decision
from .hashing import jaccard, normalize_text, sha256_bytes
from .ids import next_id
from .vocab import CHANNELS, PRODUCT_TYPES


def create_opportunity(connection, *, title, channel, product_type, niche, notes=None,
                       confirm=False, rationale=None):
    if channel not in CHANNELS or product_type not in PRODUCT_TYPES:
        raise ValueError("Geçersiz channel veya product_type")
    normalized = normalize_text(niche)
    dedup_hash = sha256_bytes(f"{channel}|{product_type}|{normalized}".encode())
    if connection.execute("SELECT 1 FROM opportunity WHERE dedup_hash=?", (dedup_hash,)).fetchone():
        raise ValueError("Aynı dedup_hash ile fırsat zaten var")
    similar = [(r["id"], jaccard(niche, r["niche"])) for r in connection.execute("SELECT id,niche FROM opportunity")]
    close = [(oid, score) for oid, score in similar if score >= .80]
    if close and not (confirm and rationale):
        raise ValueError(f"Yakın benzer fırsat: {close[0][0]}; --confirm ve gerekçe gerekli")
    oid = next_id(connection, "opportunity")
    now = isoformat_utc(utc_now())
    with connection:
        connection.execute("INSERT INTO opportunity(id,title,channel,product_type,niche,dedup_hash,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                           (oid,title,channel,product_type,niche,dedup_hash,notes,now,now))
    if close:
        log_decision(connection, entity_type="OPPORTUNITY", entity_id=oid,
                     actor="human:serhat", action="OVERRIDE", rationale=rationale)
    return oid


def activate(connection, opportunity_id):
    try:
        with connection:
            cursor = connection.execute("UPDATE opportunity SET is_active=1, updated_at=? WHERE id=?", (isoformat_utc(utc_now()), opportunity_id))
            if cursor.rowcount != 1:
                raise ValueError("Fırsat bulunamadı")
    except sqlite3.IntegrityError as exc:
        raise ValueError("Aynı anda yalnızca 1 aktif fırsat olabilir") from exc
    log_decision(connection, entity_type="OPPORTUNITY", entity_id=opportunity_id,
                 actor="human:serhat", action="ACTIVATE",
                 rationale="Kullanıcı fırsatı aktif çalışma olarak seçti")


def set_status(connection, opportunity_id, status, rationale):
    from .vocab import OPPORTUNITY_STATUSES
    if status not in OPPORTUNITY_STATUSES:
        raise ValueError(f"Geçersiz durum: {status}")
    if not rationale or not rationale.strip():
        raise ValueError("Durum değişikliği için gerekçe zorunludur")
    with connection:
        cursor = connection.execute("UPDATE opportunity SET status=?,updated_at=? WHERE id=?",
                                    (status,isoformat_utc(utc_now()),opportunity_id))
        if cursor.rowcount != 1:
            raise ValueError("Fırsat bulunamadı")
    action = {"APPROVED":"APPROVE","REJECTED":"REJECT","PARKED":"PARK"}.get(status,"CREATE")
    log_decision(connection,entity_type="OPPORTUNITY",entity_id=opportunity_id,
                 actor="human:serhat",action=action,rationale=rationale)


def link_claims(connection, opportunity_id, claim_ids):
    with connection:
        for claim_id in claim_ids:
            cursor = connection.execute("UPDATE claim SET opportunity_id=? WHERE id=?", (opportunity_id, claim_id))
            if cursor.rowcount != 1:
                raise ValueError(f"Claim bulunamadı: {claim_id}")
