import pytest

from src.opportunity import activate, create_opportunity, set_status


def test_t12_exact_and_near_duplicate_rules(connection):
    first = create_opportunity(connection, title="Space Nursery", channel="KDP", product_type="low_content", niche="space nursery wall art")
    with pytest.raises(ValueError, match="dedup_hash"):
        create_opportunity(connection, title="Same", channel="KDP", product_type="low_content", niche="art space nursery wall")
    with pytest.raises(ValueError, match="Yakın benzer"):
        create_opportunity(connection, title="Near", channel="ETSY", product_type="low_content", niche="wall art space nursery")
    second = create_opportunity(connection, title="Near", channel="ETSY", product_type="low_content", niche="wall art space nursery", confirm=True, rationale="Kanal farklı")
    assert (first, second) == ("opp_0001", "opp_0002")
    assert connection.execute("SELECT action FROM decision_log WHERE entity_id=?",(second,)).fetchone()[0] == "OVERRIDE"


def test_t15_database_enforces_single_active(connection):
    one = create_opportunity(connection, title="One", channel="KDP", product_type="book", niche="one niche")
    two = create_opportunity(connection, title="Two", channel="KDP", product_type="book", niche="two niche")
    activate(connection, one)
    with pytest.raises(ValueError, match="yalnızca 1"):
        activate(connection, two)


def test_status_is_closed_vocabulary_and_logged(connection):
    oid=create_opportunity(connection,title="One",channel="KDP",product_type="book",niche="unique niche")
    with pytest.raises(ValueError,match="Geçersiz durum"):
        set_status(connection,oid,"INVENTED","test")
    set_status(connection,oid,"APPROVED","Kanıtlar yeterli")
    assert connection.execute("SELECT status FROM opportunity WHERE id=?",(oid,)).fetchone()[0] == "APPROVED"
    assert connection.execute("SELECT action FROM decision_log WHERE entity_id=?",(oid,)).fetchone()[0] == "APPROVE"
