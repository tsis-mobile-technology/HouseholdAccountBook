import os
import json
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.core.config import DATA_DIR, BACKUP_DIR, DB_PATH

logger = logging.getLogger("gdrive_service")

GDRIVE_CREDS_FILE = DATA_DIR / "gdrive_credentials.json"
GDRIVE_CONFIG_FILE = DATA_DIR / "gdrive_config.json"
DEFAULT_FOLDER_NAME = "HouseholdAccountBook_Backups"

def load_gdrive_config() -> Dict[str, Any]:
    """Loads Google Drive integration configuration."""
    default_config = {
        "enabled": False,
        "folder_name": DEFAULT_FOLDER_NAME,
        "folder_id": None,
        "schedule": "off",  # off, daily, weekly, monthly
        "last_backup_time": None,
        "last_backup_status": None,
        "account_email": None,
        "auth_type": None,  # "service_account" or "oauth"
    }
    if GDRIVE_CONFIG_FILE.exists():
        try:
            with open(GDRIVE_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
        except Exception as e:
            logger.warning(f"Error reading gdrive_config.json: {e}")
    return default_config

def save_gdrive_config(config: Dict[str, Any]) -> None:
    """Saves Google Drive integration configuration."""
    try:
        with open(GDRIVE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving gdrive_config.json: {e}")

def get_drive_service():
    """Builds and returns the Google Drive API service using saved credentials."""
    if not GDRIVE_CREDS_FILE.exists():
        raise FileNotFoundError("구글 드라이브 인증 파일(gdrive_credentials.json)이 등록되지 않았습니다.")

    try:
        with open(GDRIVE_CREDS_FILE, "r", encoding="utf-8") as f:
            creds_data = json.load(f)
    except Exception as e:
        raise ValueError(f"인증 파일 형식이 올바르지 않습니다: {e}")

    # Check if Service Account JSON
    if creds_data.get("type") == "service_account":
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=scopes
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return service, "service_account", creds_data.get("client_email")

    # Check if OAuth Authorized User or Client Credentials
    if "refresh_token" in creds_data:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = Credentials.from_authorized_user_info(creds_data)
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return service, "oauth", creds_data.get("client_id")

    raise ValueError("지원되지 않는 인증 파일 형식입니다. Google Cloud 서비스 계정 JSON 파일이 필요합니다.")

def get_or_create_backup_folder(service, folder_name: str = DEFAULT_FOLDER_NAME) -> str:
    """Finds or creates a dedicated backup folder in Google Drive."""
    config = load_gdrive_config()
    folder_id = config.get("folder_id")

    if folder_id:
        try:
            folder = service.files().get(fileId=folder_id, fields="id, name, trashed").execute()
            if not folder.get("trashed"):
                return folder_id
        except Exception:
            pass

    # Search existing folder by name
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
    else:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        folder_id = folder.get("id")

    config["folder_id"] = folder_id
    save_gdrive_config(config)
    return folder_id

def test_drive_connection() -> Dict[str, Any]:
    """Tests connection to Google Drive and returns status."""
    if not GDRIVE_CREDS_FILE.exists():
        return {
            "connected": False,
            "message": "인증 정보가 설정되지 않았습니다.",
            "email": None,
            "folder_name": DEFAULT_FOLDER_NAME
        }

    try:
        service, auth_type, email = get_drive_service()
        folder_id = get_or_create_backup_folder(service)
        config = load_gdrive_config()
        config["enabled"] = True
        config["account_email"] = email
        config["auth_type"] = auth_type
        config["folder_id"] = folder_id
        save_gdrive_config(config)

        return {
            "connected": True,
            "auth_type": auth_type,
            "email": email,
            "folder_id": folder_id,
            "folder_name": config.get("folder_name", DEFAULT_FOLDER_NAME),
            "message": "구글 드라이브와 성공적으로 연결되었습니다."
        }
    except Exception as e:
        logger.error(f"Google Drive connection test failed: {e}")
        return {
            "connected": False,
            "message": f"연결 실패: {str(e)}",
            "email": None,
            "folder_name": DEFAULT_FOLDER_NAME
        }

def save_credentials(creds_data: Dict[str, Any]) -> Dict[str, Any]:
    """Saves Google Drive credentials and verifies connection."""
    with open(GDRIVE_CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds_data, f, ensure_ascii=False, indent=2)

    return test_drive_connection()

def upload_backup_to_drive() -> Dict[str, Any]:
    """
    Takes a snapshot of current SQLite DB and uploads it to Google Drive.
    """
    service, _, _ = get_drive_service()
    folder_id = get_or_create_backup_folder(service)

    # 1. Take a clean snapshot of SQLite DB
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"account_book_{now_str}.db"
    temp_snapshot_path = BACKUP_DIR / backup_filename

    # Ensure DB flush using SQLite VACUUM INTO or copy
    try:
        conn = sqlite3.connect(DB_PATH)
        # Flush WAL to main DB
        conn.execute("PRAGMA wal_checkpoint(FULL);")
        conn.close()
    except Exception as e:
        logger.warning(f"wal_checkpoint warning: {e}")

    shutil.copy2(DB_PATH, temp_snapshot_path)

    # 2. Upload to Google Drive
    from googleapiclient.http import MediaFileUpload

    file_metadata = {
        "name": backup_filename,
        "parents": [folder_id],
        "description": f"가계부 자동 백업 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
    }
    media = MediaFileUpload(
        str(temp_snapshot_path),
        mimetype="application/x-sqlite3",
        resumable=True
    )

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, size, createdTime"
    ).execute()

    # Update config
    config = load_gdrive_config()
    config["last_backup_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config["last_backup_status"] = "성공"
    save_gdrive_config(config)

    return {
        "status": "success",
        "file_id": uploaded_file.get("id"),
        "file_name": uploaded_file.get("name"),
        "size": uploaded_file.get("size", temp_snapshot_path.stat().st_size),
        "created_time": uploaded_file.get("createdTime"),
        "message": f"'{backup_filename}' 백업이 구글 드라이브에 안전하게 업로드되었습니다."
    }

def list_drive_backups() -> List[Dict[str, Any]]:
    """Lists backup files present in the Google Drive backup folder."""
    if not GDRIVE_CREDS_FILE.exists():
        return []

    try:
        service, _, _ = get_drive_service()
        folder_id = get_or_create_backup_folder(service)

        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            orderBy="createdTime desc",
            fields="files(id, name, size, createdTime, modifiedTime)",
            pageSize=30
        ).execute()

        files = results.get("files", [])
        return [
            {
                "id": f["id"],
                "name": f["name"],
                "size": int(f.get("size", 0)),
                "created_time": f.get("createdTime", ""),
                "modified_time": f.get("modifiedTime", "")
            }
            for f in files
        ]
    except Exception as e:
        logger.error(f"Failed to list drive backups: {e}")
        return []

def restore_from_drive_backup(file_id: str) -> Dict[str, Any]:
    """
    Downloads the selected backup file from Google Drive and restores it as the current DB.
    Also creates a safety backup of the current DB before overwriting.
    """
    service, _, _ = get_drive_service()

    # Get file metadata
    file_meta = service.files().get(fileId=file_id, fields="id, name").execute()
    filename = file_meta.get("name", "downloaded_backup.db")

    # Download file
    import io
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    download_dest = BACKUP_DIR / f"restore_temp_{filename}"

    with open(download_dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    # Validate downloaded SQLite file
    try:
        test_conn = sqlite3.connect(download_dest)
        test_cur = test_conn.cursor()
        test_cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        tables_count = test_cur.fetchone()[0]
        test_conn.close()
        if tables_count == 0:
            raise ValueError("백업 파일 내 테이블이 존재하지 않는 빈 데이터베이스입니다.")
    except Exception as e:
        if download_dest.exists():
            download_dest.unlink()
        raise ValueError(f"유효한 SQLite 백업 파일이 아닙니다: {e}")

    # Safety backup of current DB
    safety_backup = BACKUP_DIR / f"safety_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, safety_backup)

    # Overwrite current DB
    shutil.copy2(download_dest, DB_PATH)

    # Remove temp download
    try:
        download_dest.unlink()
    except Exception:
        pass

    return {
        "status": "success",
        "restored_file": filename,
        "safety_backup": safety_backup.name,
        "message": f"'{filename}' 파일로 가계부 데이터가 성공적으로 복원되었습니다."
    }

def update_backup_schedule(schedule: str) -> Dict[str, Any]:
    """Updates automatic backup schedule setting: 'off', 'daily', 'weekly', 'monthly'."""
    if schedule not in ["off", "daily", "weekly", "monthly"]:
        raise ValueError("스케줄은 'off', 'daily', 'weekly', 'monthly' 중 하나여야 합니다.")

    config = load_gdrive_config()
    config["schedule"] = schedule
    save_gdrive_config(config)
    return {
        "status": "success",
        "schedule": schedule,
        "message": f"자동 백업 주기가 '{schedule}'(으)로 변경되었습니다."
    }
