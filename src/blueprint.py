from __future__ import annotations

from dataclasses import dataclass

from .review import OpportunityReview


@dataclass(frozen=True)
class BlueprintPreview:
    opportunity_id: str
    title: str
    channel: str
    product_type: str
    niche: str
    observed_price_range: str
    unlocked: bool
    unknown_fields: tuple[str, ...]


def build_blueprint_preview(review: OpportunityReview) -> BlueprintPreview:
    price = "UNKNOWN"
    if review.price_min is not None:
        price = f"{review.price_min:.2f}–{review.price_max:.2f} {review.currency or ''}".strip()
    return BlueprintPreview(
        opportunity_id=review.id,
        title=review.title,
        channel=review.channel,
        product_type=review.product_type,
        niche=review.niche,
        observed_price_range=price,
        unlocked=review.status == "APPROVED",
        unknown_fields=(
            "Hedef yaş aralığı",
            "Temel müşteri problemi",
            "Ürün vaadi",
            "Sayfa ve aktivite sayısı",
            "Özgün farklılaştırıcı",
            "Nihai fiyat",
            "İçerik yapısı",
            "IP / marka kontrolü",
        ),
    )
