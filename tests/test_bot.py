from src.bot import advance_run, create_run
from src.opportunity import create_opportunity


def test_bot_checkpoints_and_waits_for_human(connection):
    oid = create_opportunity(connection, title="Bot test", channel="ETSY", product_type="printable", niche="bot test")
    run_id = create_run(connection, oid)
    assert connection.execute("SELECT COUNT(*) FROM bot_task WHERE run_id=?", (run_id,)).fetchone()[0] == 4
    assert advance_run(connection, run_id) == "BLOCKED"
    run = connection.execute("SELECT status,last_error FROM bot_run WHERE id=?", (run_id,)).fetchone()
    assert run["status"] == "BLOCKED"
    assert "Kanıt kapısı" in run["last_error"]


def test_only_one_open_bot_run(connection):
    first = create_opportunity(connection, title="First", channel="ETSY", product_type="printable", niche="first bot")
    second = create_opportunity(connection, title="Second", channel="KDP", product_type="book", niche="second bot")
    create_run(connection, first)
    try:
        create_run(connection, second)
        assert False, "İkinci açık run reddedilmeliydi"
    except ValueError as exc:
        assert "yalnız bir" in str(exc)
