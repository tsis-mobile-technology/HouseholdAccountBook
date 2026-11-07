import pytest
from app.core import config, network
from fastapi.testclient import TestClient
from app.main import app

def test_meta_network_info_response():
    client = TestClient(app)
    res = client.get("/api/meta/network-info")
    assert res.status_code == 200
    data = res.json()
    assert "protocol" in data
    assert "use_https" in data
    assert data["pc_url"].startswith(data["protocol"] + "://")
    assert data["mobile_url"].startswith(data["protocol"] + "://")
    assert "qr_code" in data

def test_ssl_resolve_logic(tmp_path, monkeypatch):
    cert_file = tmp_path / "test_cert.pem"
    key_file = tmp_path / "test_key.pem"
    cert_file.write_text("DUMMY CERT")
    key_file.write_text("DUMMY KEY")

    # Test explicit env resolution
    monkeypatch.setattr(config, "SSL_CERTFILE_ENV", str(cert_file))
    monkeypatch.setattr(config, "SSL_KEYFILE_ENV", str(key_file))

    resolved_cert, resolved_key = config._resolve_ssl_files()
    assert resolved_cert == str(cert_file)
    assert resolved_key == str(key_file)

def test_ssl_auto_detect_in_certs_dir(tmp_path, monkeypatch):
    certs_dir = tmp_path / "certs"
    certs_dir.mkdir()
    (certs_dir / "fullchain.pem").write_text("DUMMY CERT")
    (certs_dir / "privkey.pem").write_text("DUMMY KEY")

    monkeypatch.setattr(config, "SSL_CERTFILE_ENV", None)
    monkeypatch.setattr(config, "SSL_KEYFILE_ENV", None)
    monkeypatch.setattr(config, "CERTS_DIR", certs_dir)

    resolved_cert, resolved_key = config._resolve_ssl_files()
    assert resolved_cert == str(certs_dir / "fullchain.pem")
    assert resolved_key == str(certs_dir / "privkey.pem")
