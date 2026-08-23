from src.dashboard import render_review
from src.opportunity import create_opportunity
from src.review import load_review


def test_review_never_invents_missing_metrics(connection):
    oid = create_opportunity(
        connection, title="Test fırsatı", channel="ETSY",
        product_type="printable", niche="test niche"
    )
    review = load_review(connection, oid)
    html = render_review(review)
    assert review.claim_count == 0
    assert "UNKNOWN" in html
    assert "ONAYLA" in html
    assert "Talep, kârlılık veya başarı puanı uydurmaz" in html
