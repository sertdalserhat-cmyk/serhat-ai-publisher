from src.blueprint import build_blueprint_preview
from src.dashboard import render_blueprint
from src.opportunity import create_opportunity
from src.review import load_review


def test_blueprint_is_locked_and_unknowns_stay_unknown(connection):
    oid = create_opportunity(
        connection, title="Blueprint test", channel="ETSY",
        product_type="printable", niche="nursery"
    )
    preview = build_blueprint_preview(load_review(connection, oid))
    html = render_blueprint(preview)
    assert preview.unlocked is False
    assert "KİLİTLİ" in html
    assert "UNKNOWN" in html
    assert "İnsan kararı gereken alanlar" in html
