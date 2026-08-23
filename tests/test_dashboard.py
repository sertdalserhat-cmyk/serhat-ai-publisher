from src.dashboard import render_dashboard


def test_dashboard_has_start_button_and_manual_first_notice():
    html = render_dashboard()
    assert 'id="start"' in html
    assert "BAŞLAT" in html
    assert "MANUAL-FIRST" in html
    assert "Bilinmeyen veriyi uydurmaz" in html
