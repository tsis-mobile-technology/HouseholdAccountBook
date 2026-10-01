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
GDRIVE_CLIENT_SECRET_FILE = DATA_DIR / "gdrive_client_secret.json"
DEFAULT_FOLDER_NAME = "HouseholdAccountBook_Backups"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

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
        "auth_type": None,  # "oauth" or "service_account"
        "warning": None,
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

def get_oauth_client_config() -> Optional[Dict[str, Any]]:
    """Loads OAuth client configuration from file."""
    if not GDRIVE_CLIENT_SECRET_FILE.exists():
        return None
    try:
        with open(GDRIVE_CLIENT_SECRET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading {GDRIVE_CLIENT_SECRET_FILE}: {e}")
        return None

def save_oauth_client_config(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Saves OAuth client configuration."""
    if "client_id" in client_data and "client_secret" in client_data:
        config = {
            "web": {
                "client_id": client_data["client_id"].strip(),
                "client_secret": client_data["client_secret"].strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
    elif "web" in client_data or "installed" in client_data:
        config = client_data
    else:
        raise ValueError("유효한 OAuth 2.0 클라이언트 정보(client_id, client_secret)가 필요합니다.")

    with open(GDRIVE_CLIENT_SECRET_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "message": "OAuth 2.0 클라이언트 정보가 성공적으로 저장되었습니다."
    }

_OAUTH_STATES_FILE = DATA_DIR / ".oauth_states.json"

def _save_oauth_state(state: str, code_verifier: Optional[str]) -> None:
    """Persists PKCE code_verifier associated with the OAuth state."""
    states = {}
    if _OAUTH_STATES_FILE.exists():
        try:
            with open(_OAUTH_STATES_FILE, "r", encoding="utf-8") as f:
                states = json.load(f)
        except Exception:
            states = {}
    states[state] = {
        "code_verifier": code_verifier,
        "created_at": datetime.now().isoformat()
    }
    # Keep only the latest 20 states to prevent unbounded growth
    if len(states) > 20:
        sorted_keys = sorted(states.keys(), key=lambda k: states[k].get("created_at", ""))
        for k in sorted_keys[:-20]:
            states.pop(k, None)
    try:
        with open(_OAUTH_STATES_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f)
    except Exception as e:
        logger.warning(f"Failed to persist oauth state: {e}")

def _pop_oauth_code_verifier(state: Optional[str]) -> Optional[str]:
    """Retrieves and removes PKCE code_verifier for the given state."""
    if not _OAUTH_STATES_FILE.exists():
        return None
    try:
        with open(_OAUTH_STATES_FILE, "r", encoding="utf-8") as f:
            states = json.load(f)

        verifier = None
        if state and state in states:
            verifier = states.pop(state, {}).get("code_verifier")
        elif states:
            # Fallback to the latest verifier if state is not matched
            latest_key = max(states.keys(), key=lambda k: states[k].get("created_at", ""))
            verifier = states.pop(latest_key, {}).get("code_verifier")

        with open(_OAUTH_STATES_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f)
        return verifier
    except Exception as e:
        logger.warning(f"Failed to read oauth state: {e}")
        return None

def get_oauth_authorization_url(redirect_uri: str) -> str:
    """Generates Google OAuth 2.0 consent authorization URL."""
    client_config = get_oauth_client_config()
    if not client_config:
        raise FileNotFoundError("OAuth 클라이언트 정보(gdrive_client_secret.json)가 설정되지 않았습니다. 먼저 클라이언트 키를 등록해주세요.")

    import google_auth_oauthlib.flow
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=DEFAULT_SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    _save_oauth_state(state, flow.code_verifier)
    return auth_url

def complete_oauth_flow(code: str, redirect_uri: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Exchanges authorization code for credentials and saves them."""
    client_config = get_oauth_client_config()
    if not client_config:
        raise FileNotFoundError("OAuth 클라이언트 설정 파일이 존재하지 않습니다.")

    import google_auth_oauthlib.flow
    from googleapiclient.discovery import build
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    code_verifier = _pop_oauth_code_verifier(state)

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=DEFAULT_SCOPES,
        redirect_uri=redirect_uri,
        state=state
    )
    if code_verifier:
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code, code_verifier=code_verifier)
    else:
        flow.fetch_token(code=code)

    credentials = flow.credentials

    # Test Drive service and retrieve user email
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    user_email = "Google User"
    try:
        about = service.about().get(fields="user(emailAddress, displayName)", supportsAllDrives=True).execute()
        user_info = about.get("user", {})
        user_email = user_info.get("emailAddress") or user_info.get("displayName") or "Google User"
    except Exception as e:
        logger.warning(f"Failed to fetch user info: {e}")

    token_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "user_email": user_email
    }

    with open(GDRIVE_CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(token_dict, f, ensure_ascii=False, indent=2)

    folder_id = get_or_create_backup_folder(service)

    config = load_gdrive_config()
    config["enabled"] = True
    config["account_email"] = user_email
    config["auth_type"] = "oauth"
    config["folder_id"] = folder_id
    config["warning"] = None
    save_gdrive_config(config)

    return {
        "status": "success",
        "email": user_email,
        "folder_id": folder_id,
        "message": f"구글 계정 ({user_email})과 성공적으로 연동되었습니다."
    }

def disconnect_drive() -> Dict[str, Any]:
    """Disconnects Google Drive and clears saved credentials."""
    if GDRIVE_CREDS_FILE.exists():
        try:
            GDRIVE_CREDS_FILE.unlink()
        except Exception as e:
            logger.warning(f"Error removing credentials file: {e}")

    config = load_gdrive_config()
    config["enabled"] = False
    config["account_email"] = None
    config["auth_type"] = None
    config["folder_id"] = None
    config["last_backup_status"] = None
    config["warning"] = None
    save_gdrive_config(config)

    return {
        "status": "success",
        "message": "구글 드라이브 연동이 해제되었습니다."
    }

def set_backup_folder_id(folder_id: Optional[str]) -> Dict[str, Any]:
    """Sets a custom backup folder ID (especially for Shared Drives)."""
    f_id = folder_id.strip() if folder_id else None
    config = load_gdrive_config()
    config["folder_id"] = f_id
    save_gdrive_config(config)
    return {
        "status": "success",
        "folder_id": f_id,
        "message": f"백업 폴더 ID가 {'설정' if f_id else '초기화'}되었습니다."
    }

def get_drive_service():
    """Builds and returns the Google Drive API service using saved credentials."""
    if not GDRIVE_CREDS_FILE.exists():
        raise FileNotFoundError("구글 드라이브 인증 정보(gdrive_credentials.json)가 등록되지 않았습니다.")

    try:
        with open(GDRIVE_CREDS_FILE, "r", encoding="utf-8") as f:
            creds_data = json.load(f)
    except Exception as e:
        raise ValueError(f"인증 파일 형식이 올바르지 않습니다: {e}")

    # 1. Check if OAuth Authorized User or token info
    if "refresh_token" in creds_data or ("token" in creds_data and "client_id" in creds_data):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = Credentials.from_authorized_user_info(creds_data)
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        email = creds_data.get("user_email")
        if not email:
            try:
                about = service.about().get(fields="user(emailAddress)", supportsAllDrives=True).execute()
                email = about.get("user", {}).get("emailAddress", "OAuth User")
            except Exception:
                email = creds_data.get("client_id", "OAuth User")
        return service, "oauth", email

    # 2. Check if Service Account JSON
    if creds_data.get("type") == "service_account":
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=scopes
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return service, "service_account", creds_data.get("client_email")

    raise ValueError("지원되지 않는 인증 파일 형식입니다. OAuth 토큰 또는 Google Cloud 서비스 계정 JSON 파일이 필요합니다.")

def get_or_create_backup_folder(service, folder_name: str = DEFAULT_FOLDER_NAME) -> str:
    """Finds or creates a dedicated backup folder in Google Drive."""
    config = load_gdrive_config()
    folder_id = config.get("folder_id")

    if folder_id:
        try:
            folder = service.files().get(
                fileId=folder_id,
                fields="id, name, trashed, driveId",
                supportsAllDrives=True
            ).execute()
            if not folder.get("trashed"):
                return folder_id
        except Exception as e:
            logger.warning(f"Specified folder_id {folder_id} is invalid or inaccessible: {e}")

    # Search existing folder by name
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        files = results.get("files", [])
    except Exception as e:
        logger.warning(f"Error searching existing backup folder: {e}")
        files = []

    if files:
        folder_id = files[0]["id"]
    else:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(
            body=file_metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()
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

        # Check for service account quota limitation on personal drives
        warning_msg = None
        if auth_type == "service_account":
            try:
                folder_meta = service.files().get(
                    fileId=folder_id,
                    fields="id, name, driveId",
                    supportsAllDrives=True
                ).execute()
                if not folder_meta.get("driveId"):
                    warning_msg = (
                        "⚠️ 주의: Google 서비스 계정(Service Account)은 구글 정책상 기본 저장 용량이 0 Byte로 제한되어 있어 "
                        "개인 드라이브에는 백업 파일을 업로드할 수 없습니다. "
                        "개인 구글 계정(@gmail.com)은 'Google 계정 로그인 (OAuth 2.0)' 방식을 이용하시거나, "
                        "Google Workspace '공유 드라이브' 폴더 ID를 지정해주세요."
                    )
            except Exception as fe:
                logger.warning(f"Could not verify folder driveId: {fe}")

        config["warning"] = warning_msg
        save_gdrive_config(config)

        return {
            "connected": True,
            "auth_type": auth_type,
            "email": email,
            "folder_id": folder_id,
            "folder_name": config.get("folder_name", DEFAULT_FOLDER_NAME),
            "warning": warning_msg,
            "message": warning_msg if warning_msg else "구글 드라이브와 성공적으로 연결되었습니다."
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
    """Saves Google Drive credentials or OAuth client file."""
    # Check if OAuth Client Secrets file
    if "web" in creds_data or "installed" in creds_data:
        save_oauth_client_config(creds_data)
        client_id = (
            creds_data.get("web", {}).get("client_id") or
            creds_data.get("installed", {}).get("client_id") or
            ""
        )
        return {
            "status": "oauth_client_ready",
            "auth_type": "oauth_client",
            "client_id": client_id,
            "message": "OAuth 2.0 클라이언트 파일이 등록되었습니다. 'Google 계정 로그인 (OAuth 2.0)' 버튼을 눌러 연동을 완료하세요."
        }

    # Otherwise save credentials file
    with open(GDRIVE_CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds_data, f, ensure_ascii=False, indent=2)

    return test_drive_connection()

def upload_backup_to_drive() -> Dict[str, Any]:
    """
    Takes a snapshot of current SQLite DB and uploads it to Google Drive.
    """
    service, auth_type, _ = get_drive_service()
    folder_id = get_or_create_backup_folder(service)

    # 1. Take a clean snapshot of SQLite DB
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"account_book_{now_str}.db"
    temp_snapshot_path = BACKUP_DIR / backup_filename

    # Ensure DB flush using SQLite WAL checkpoint
    try:
        conn = sqlite3.connect(DB_PATH)
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

    try:
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, size, createdTime",
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        err_msg = str(e)
        if "storageQuotaExceeded" in err_msg or "Service Accounts do not have storage quota" in err_msg:
            raise RuntimeError(
                "Google 정책 변경으로 인해 서비스 계정(Service Account)은 기본 저장 용량이 0 Byte로 제한되어 있어 "
                "개인 Google Drive(My Drive)에는 백업 파일을 업로드할 수 없습니다.\n\n"
                "💡 해결 방법:\n"
                "1. 개인 구글 계정(@gmail.com) 사용 시: [연동 해제] 후 'Google 계정 로그인 (OAuth 2.0)' 방식을 이용하세요. (개인 드라이브 15GB 무료 사용)\n"
                "2. Google Workspace 사용 시: '공유 드라이브(Shared Drive)'를 생성하여 서비스 계정을 구성원으로 추가하고 폴더 ID를 설정하세요."
            )
        raise

    # Update config
    config = load_gdrive_config()
    config["last_backup_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config["last_backup_status"] = "성공"
    config["warning"] = None
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
            pageSize=30,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
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

def delete_drive_backup(file_id: str) -> Dict[str, Any]:
    """Deletes a backup file from Google Drive."""
    service, _, _ = get_drive_service()
    service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
    return {
        "status": "success",
        "message": "구글 드라이브 백업 파일이 삭제되었습니다."
    }

def restore_from_drive_backup(file_id: str) -> Dict[str, Any]:
    """
    Downloads the selected backup file from Google Drive and restores it as the current DB.
    Also creates a safety backup of the current DB before overwriting.
    """
    service, _, _ = get_drive_service()

    # Get file metadata
    file_meta = service.files().get(
        fileId=file_id,
        fields="id, name",
        supportsAllDrives=True
    ).execute()
    filename = file_meta.get("name", "downloaded_backup.db")

    # Download file
    import io
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
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
