from __future__ import annotations

from dataclasses import dataclass


DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
PLATFORM_REPORTED_COUNT = "PLATFORM_REPORTED_COUNT"


@dataclass(frozen=True)
class ClaimType:
    family: str
    value_kind: str
    unit: str | None
    ttl_days: int
    semantics: str = DIRECT_OBSERVATION


SOURCE_FAMILIES = {
    "AMAZON_KDP": ("B", "PUBLIC_MANUAL"),
    "ETSY": ("B", "PUBLIC_MANUAL"),
    "YOUTUBE": ("B", "PUBLIC_MANUAL"),
    "GOOGLE_BOOKS": ("A", "OFFICIAL_API"),
    "OPEN_LIBRARY": ("A", "OFFICIAL_API"),
    "USPTO": ("A", "PUBLIC_MANUAL"),
    "GOOGLE_TRENDS": ("C", "PUBLIC_MANUAL"),
    "THIRD_PARTY_TOOL": ("C", "LICENSED_TOOL"),
    "REDDIT": ("D", "PUBLIC_MANUAL"),
    "FORUM": ("D", "PUBLIC_MANUAL"),
    "OWN_SALES": ("A", "LICENSED_TOOL"),
}

CONFIDENCE_BY_RELIABILITY = {"A": "HIGH", "B": "MEDIUM", "C": "LOW", "D": "LOW"}
SOURCE_KINDS = {"MANUAL_PASTE", "MANUAL_FILE", "MANUAL_SCREENSHOT", "API"}
CHANNELS = {"KDP", "ETSY", "BOTH"}
PRODUCT_TYPES = {"book", "ebook", "low_content", "printable", "digital_download"}
OPPORTUNITY_STATUSES = {"DRAFT", "RESEARCHING", "READY_FOR_REVIEW", "APPROVED", "REJECTED", "PARKED"}


def _c(family, kind, unit, ttl, semantics=DIRECT_OBSERVATION):
    return ClaimType(family, kind, unit, ttl, semantics)


CLAIM_TYPES = {
    "AMZ_SEARCH_RESULT_COUNT": _c("AMAZON_KDP", "num", "count", 7, PLATFORM_REPORTED_COUNT),
    "AMZ_BSR": _c("AMAZON_KDP", "num", "rank", 7),
    "AMZ_PRICE": _c("AMAZON_KDP", "num", "USD", 7),
    "AMZ_REVIEW_COUNT": _c("AMAZON_KDP", "num", "count", 30),
    "AMZ_REVIEW_RATING": _c("AMAZON_KDP", "num", "stars", 30),
    "AMZ_PUBLISH_DATE": _c("AMAZON_KDP", "text", None, 180),
    "AMZ_CATEGORY_PATH": _c("AMAZON_KDP", "text", None, 90),
    "AMZ_BESTSELLER_TITLE": _c("AMAZON_KDP", "text", None, 30),
    "AMZ_AUTOCOMPLETE_SUGGESTION": _c("AMAZON_KDP", "text", None, 30),
    "AMZ_REVIEW_TEXT": _c("AMAZON_KDP", "text", None, 180),
    "ETSY_LISTING_COUNT": _c("ETSY", "num", "count", 7, PLATFORM_REPORTED_COUNT),
    "ETSY_PRICE": _c("ETSY", "num", "USD", 7),
    "ETSY_SHOP_SALES": _c("ETSY", "num", "count", 14),
    "ETSY_FAVORITES": _c("ETSY", "num", "count", 14),
    "ETSY_IS_PERSONALIZABLE": _c("ETSY", "text", None, 90),
    "ETSY_TAG": _c("ETSY", "text", None, 30),
    "ETSY_REVIEW_TEXT": _c("ETSY", "text", None, 180),
    "YT_RESULT_COUNT": _c("YOUTUBE", "num", "count", 30, PLATFORM_REPORTED_COUNT),
    "YT_VIDEO_VIEWS": _c("YOUTUBE", "num", "count", 30),
    "YT_VIDEO_TITLE": _c("YOUTUBE", "text", None, 90),
    "YT_COMMENT_TEXT": _c("YOUTUBE", "text", None, 180),
    "GB_TITLE_COUNT": _c("GOOGLE_BOOKS", "num", "count", 90, PLATFORM_REPORTED_COUNT),
    "GB_BOOK_META": _c("GOOGLE_BOOKS", "text", None, 180),
    "OL_SUBJECT_WORK_COUNT": _c("OPEN_LIBRARY", "num", "count", 90, PLATFORM_REPORTED_COUNT),
    "OL_SUBJECT_LABEL": _c("OPEN_LIBRARY", "text", None, 180),
    "USPTO_MARK_HIT": _c("USPTO", "text", None, 180),
    "USPTO_MARK_STATUS": _c("USPTO", "text", None, 180),
    "USPTO_NO_MATCH_IN_SEARCH_SCOPE": _c("USPTO", "text", None, 180),
    "TRENDS_INTEREST_INDEX": _c("GOOGLE_TRENDS", "num", "index_0_100", 30),
    "TRENDS_RELATED_QUERY": _c("GOOGLE_TRENDS", "text", None, 30),
    "TOOL_EST_SEARCH_VOLUME": _c("THIRD_PARTY_TOOL", "num", "count_est", 30),
    "TOOL_EST_MONTHLY_REVENUE": _c("THIRD_PARTY_TOOL", "num", "USD_est", 30),
    "TOOL_COMPETITION_SCORE": _c("THIRD_PARTY_TOOL", "num", "score", 30),
    "CUSTOMER_COMPLAINT": _c("FORUM", "text", None, 365),
    "MISSING_FEATURE": _c("FORUM", "text", None, 365),
    "PURCHASE_DRIVER": _c("FORUM", "text", None, 365),
    "OWN_UNITS_SOLD": _c("OWN_SALES", "num", "count", 0),
    "OWN_REVENUE": _c("OWN_SALES", "num", "USD", 0),
    "OWN_IMPRESSIONS": _c("OWN_SALES", "num", "count", 0),
}


def require_claim_type(name: str) -> ClaimType:
    try:
        return CLAIM_TYPES[name]
    except KeyError as exc:
        valid = ", ".join(sorted(CLAIM_TYPES))
        raise ValueError(f"Geçersiz claim_type: {name}. Geçerli tipler: {valid}") from exc


def require_source_family(name: str) -> tuple[str, str]:
    try:
        return SOURCE_FAMILIES[name]
    except KeyError as exc:
        raise ValueError(f"Geçersiz source_family: {name}") from exc
