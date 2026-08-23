from __future__ import annotations

import html
from pathlib import Path

from .staleness import stale_claim_ids
from .vocab import PLATFORM_REPORTED_COUNT, require_claim_type


def generate_report(connection, *, opportunity_id, out_path, fresh=False, now=None):
    opportunity = connection.execute("SELECT * FROM opportunity WHERE id=?", (opportunity_id,)).fetchone()
    if not opportunity:
        raise ValueError("Fırsat bulunamadı")
    stale = set(stale_claim_ids(connection, now)) if fresh else set()
    rows = [r for r in connection.execute("""SELECT c.*,s.url,s.retrieved_at,s.source_family
        FROM claim c JOIN source s ON s.id=c.source_id WHERE c.opportunity_id=? ORDER BY c.id""", (opportunity_id,)) if r["id"] not in stale]
    unbound = connection.execute("SELECT COUNT(*) FROM claim WHERE opportunity_id IS NULL").fetchone()[0]
    items = []
    for row in rows:
        value = row["value_num"] if row["value_num"] is not None else row["value_text"]
        rendered_value = f"{value} {row['unit']}" if row["value_num"] is not None and row["unit"] else str(value)
        note = " <em>(platformun bildirdiği yaklaşık sayı)</em>" if require_claim_type(row["claim_type"]).semantics == PLATFORM_REPORTED_COUNT else ""
        items.append(f"<li><strong>{html.escape(row['claim_type'])}</strong>: {html.escape(rendered_value)}{note}<br>Kaynak: {html.escape(row['source_id'])} — <a href=\"{html.escape(row['url'] or '')}\">{html.escape(row['url'] or 'URL yok')}</a> — {html.escape(row['retrieved_at'])}<br>Alıntı/konum: {html.escape(row['quote'] or row['locator'] or '')}</li>")
    body = f"<!doctype html><html lang='tr'><meta charset='utf-8'><title>{html.escape(opportunity['title'])}</title><body><h1>{html.escape(opportunity['title'])}</h1><p>Bağsız iddia sayısı: {unbound}</p><ul>{''.join(items)}</ul></body></html>"
    path = Path(out_path)
    path.write_text(body, encoding="utf-8")
    return path
