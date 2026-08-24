import pytest

from src.blueprint_store import save_blueprint
from src.opportunity import create_opportunity, set_status


DATA = {
    "audience": "3-6 yaş çocuğu olan ebeveynler",
    "customer_problem": "Yazdırılabilir eğitici aktivite ihtiyacı",
    "product_promise": "Yaşa uygun, uygulanabilir aktivite paketi",
    "age_min": 3, "age_max": 6, "page_count": 80, "activity_count": 30,
    "differentiator": "Net ilerleme yapısı", "target_price": 149.0,
    "currency": "TRY", "content_structure": "5 bölüm",
}


def test_blueprint_requires_human_approved_opportunity(connection):
    oid = create_opportunity(connection, title="Test", channel="ETSY",
                             product_type="printable", niche="test blueprint")
    with pytest.raises(ValueError, match="APPROVED"):
        save_blueprint(connection, oid, DATA)
    set_status(connection, oid, "APPROVED", "Kanıtlar insan tarafından incelendi")
    assert save_blueprint(connection, oid, DATA) == 1
    assert save_blueprint(connection, oid, {**DATA, "page_count": 90}) == 2
    row = connection.execute(
        "SELECT page_count,version FROM product_blueprint WHERE opportunity_id=?", (oid,)
    ).fetchone()
    assert tuple(row) == (90, 2)
