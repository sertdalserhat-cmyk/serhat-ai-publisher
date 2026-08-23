from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from src.db import initialize
from src.opportunity import create_opportunity
from src.webapp import make_handler


def test_dashboard_routes_and_human_decision(tmp_path: Path):
    db_path = tmp_path / "publisher.db"
    evidence = tmp_path / "evidence"
    conn = initialize(db_path)
    oid = create_opportunity(
        conn, title="Nursery test", channel="ETSY",
        product_type="printable", niche="nursery test"
    )
    conn.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path, evidence))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        home = urlopen(base + "/", timeout=2).read().decode("utf-8")
        review = urlopen(base + "/review", timeout=2).read().decode("utf-8")
        blueprint = urlopen(base + "/blueprint", timeout=2).read().decode("utf-8")
        try:
            urlopen(
                Request(
                    base + "/decision",
                    data=b"status=APPROVED&rationale=Accidental+click",
                    method="POST",
                ), timeout=2,
            )
            assert False, "Açık onaysız karar reddedilmeliydi"
        except HTTPError as exc:
            assert exc.code == 400
        decision = urlopen(
            Request(
                base + "/decision",
                data=b"status=PARKED&rationale=More+evidence+needed&confirm=YES",
                method="POST",
            ),
            timeout=2,
        ).read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert "BAŞLAT" in home
    assert "Nursery test" in review
    assert "İNSAN KARAR KAPISI" in review
    assert "PRODUCT BLUEPRINT" in blueprint
    assert "KİLİTLİ" in blueprint
    assert "Karar kaydedildi" in decision

    conn = initialize(db_path)
    assert conn.execute("SELECT status FROM opportunity WHERE id=?", (oid,)).fetchone()[0] == "PARKED"
    row = conn.execute(
        "SELECT actor, action, rationale FROM decision_log WHERE entity_id=?", (oid,)
    ).fetchone()
    conn.close()
    assert tuple(row) == ("human:serhat", "PARK", "More evidence needed")
