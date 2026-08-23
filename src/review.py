from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class OpportunityReview:
    id: str
    title: str
    channel: str
    product_type: str
    niche: str
    status: str
    claim_count: int
    source_count: int
    claim_types: tuple[tuple[str, int], ...]
    confidence_counts: tuple[tuple[str, int], ...]
    price_min: float | None
    price_max: float | None
    currency: str | None
    review_count_max: float | None
    rating_min: float | None
    rating_max: float | None


def load_review(conn: sqlite3.Connection, opportunity_id: str | None = None) -> OpportunityReview:
    if opportunity_id:
        opportunity = conn.execute(
            "SELECT * FROM opportunity WHERE id=?", (opportunity_id,)
        ).fetchone()
    else:
        opportunity = conn.execute(
            """SELECT * FROM opportunity
               ORDER BY CASE WHEN is_active=1 THEN 0 ELSE 1 END, created_at DESC LIMIT 1"""
        ).fetchone()
    if not opportunity:
        raise ValueError("İncelenecek fırsat bulunamadı")

    oid = opportunity["id"]
    claim_count, source_count = conn.execute(
        """SELECT COUNT(*), COUNT(DISTINCT source_id) FROM claim
           WHERE opportunity_id=? AND status='ACTIVE'""", (oid,)
    ).fetchone()
    claim_types = tuple(
        (row["claim_type"], row["n"])
        for row in conn.execute(
            """SELECT claim_type, COUNT(*) n FROM claim
               WHERE opportunity_id=? AND status='ACTIVE'
               GROUP BY claim_type ORDER BY n DESC, claim_type""", (oid,)
        )
    )
    confidence_counts = tuple(
        (row["confidence"], row["n"])
        for row in conn.execute(
            """SELECT confidence, COUNT(*) n FROM claim
               WHERE opportunity_id=? AND status='ACTIVE'
               GROUP BY confidence ORDER BY confidence""", (oid,)
        )
    )

    def range_for(claim_type: str):
        return conn.execute(
            """SELECT MIN(value_num), MAX(value_num), MIN(unit) FROM claim
               WHERE opportunity_id=? AND status='ACTIVE' AND claim_type=?""",
            (oid, claim_type),
        ).fetchone()

    price_min, price_max, currency = range_for("ETSY_PRICE")
    _, review_count_max, _ = range_for("ETSY_REVIEW_COUNT")
    rating_min, rating_max, _ = range_for("ETSY_REVIEW_RATING")
    return OpportunityReview(
        id=oid, title=opportunity["title"], channel=opportunity["channel"],
        product_type=opportunity["product_type"], niche=opportunity["niche"],
        status=opportunity["status"], claim_count=claim_count,
        source_count=source_count, claim_types=claim_types,
        confidence_counts=confidence_counts, price_min=price_min,
        price_max=price_max, currency=currency, review_count_max=review_count_max,
        rating_min=rating_min, rating_max=rating_max,
    )
