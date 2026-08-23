import pytest

from src.secrets_scan import SECRET_LITERALS, SecretDetectedError, scan_for_secrets
from src.ingest import ingest


def test_t17_secret_literal_rejects_before_write(tmp_path):
    target = tmp_path / "evidence.txt"
    data = b"ordinary line\napi_key=do-not-store\n"
    with pytest.raises(SecretDetectedError) as error:
        scan_for_secrets(data)
    assert "satır 2" in str(error.value)
    assert "api_key=" in str(error.value)
    assert not target.exists()


def test_secret_scanner_is_the_frozen_literal_list_only():
    assert len(SECRET_LITERALS) == 11
    scan_for_secrets(b"a long random-looking value 0123456789abcdefghijklmnopqrstuvwxyz")


def test_binary_screenshot_bytes_do_not_trigger_text_secret_scan(connection,tmp_path):
    result=ingest(connection,data=b"PNG-binary-sk-random",source_family="ETSY",
                  kind="MANUAL_SCREENSHOT",url="https://example.test",locale="TR",
                  retrieved_at="2026-08-24T02:11:52+03:00",file_name="shot.png",
                  evidence_dir=tmp_path/"evidence")
    assert result.source_id == "src_000001"
