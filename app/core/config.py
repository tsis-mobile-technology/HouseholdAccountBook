import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = BASE_DIR / "exports"
STATIC_DIR = BASE_DIR / "app" / "static"
CERTS_DIR = BASE_DIR / "certs"

DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "account_book.db")))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# SSL / HTTPS Configuration
SSL_CERTFILE_ENV = os.getenv("SSL_CERTFILE")
SSL_KEYFILE_ENV = os.getenv("SSL_KEYFILE")
SSL_KEYFILE_PASSWORD = os.getenv("SSL_KEYFILE_PASSWORD")

def _resolve_ssl_files():
    cert_path = None
    key_path = None

    # 1. Explicit environment variables or .env
    if SSL_CERTFILE_ENV and SSL_KEYFILE_ENV:
        cp = Path(SSL_CERTFILE_ENV).expanduser()
        kp = Path(SSL_KEYFILE_ENV).expanduser()
        if not cp.is_absolute():
            cp = BASE_DIR / cp
        if not kp.is_absolute():
            kp = BASE_DIR / kp
        if cp.is_file() and kp.is_file():
            return str(cp), str(kp)

    # 2. Auto-detect from certs/ directory
    if CERTS_DIR.is_dir():
        cert_candidates = ["cert.pem", "fullchain.pem", "certificate.crt", "server.crt"]
        key_candidates = ["key.pem", "privkey.pem", "private.key", "server.key"]

        for c_name in cert_candidates:
            c_file = CERTS_DIR / c_name
            if c_file.is_file():
                cert_path = str(c_file)
                break

        for k_name in key_candidates:
            k_file = CERTS_DIR / k_name
            if k_file.is_file():
                key_path = str(k_file)
                break

    if cert_path and key_path:
        return cert_path, key_path

    return None, None

SSL_CERTFILE, SSL_KEYFILE = _resolve_ssl_files()
USE_HTTPS = bool(SSL_CERTFILE and SSL_KEYFILE)
PROTOCOL = "https" if USE_HTTPS else "http"

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
CERTS_DIR.mkdir(parents=True, exist_ok=True)
