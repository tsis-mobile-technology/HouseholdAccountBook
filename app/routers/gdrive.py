import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.gdrive_service import (
    load_gdrive_config,
    test_drive_connection,
    save_credentials,
    upload_backup_to_drive,
    list_drive_backups,
    delete_drive_backup,
    restore_from_drive_backup,
    update_backup_schedule,
    disconnect_drive,
    set_backup_folder_id,
    save_oauth_client_config,
    get_oauth_authorization_url,
    complete_oauth_flow,
    GDRIVE_CREDS_FILE,
    GDRIVE_CLIENT_SECRET_FILE,
)
from app.core.config import BACKUP_DIR

logger = logging.getLogger("gdrive_router")

router = APIRouter(prefix="/api/gdrive", tags=["Google Drive"])

class ScheduleUpdateRequest(BaseModel):
    schedule: str  # off, daily, weekly, monthly

class FolderIdRequest(BaseModel):
    folder_id: Optional[str] = None

class OAuthClientRequest(BaseModel):
    client_id: str
    client_secret: str

class OAuthCodeRequest(BaseModel):
    code: str
    state: Optional[str] = None
    redirect_uri: Optional[str] = None

@router.get("/status")
def get_status():
    """Returns the current Google Drive backup configuration and status."""
    config = load_gdrive_config()
    has_creds = GDRIVE_CREDS_FILE.exists()
    has_client_secret = GDRIVE_CLIENT_SECRET_FILE.exists()

    # Count local backups
    local_backups = sorted(BACKUP_DIR.glob("account_book_*.db"), reverse=True)
    local_backup_count = len(local_backups)
    last_local_backup = local_backups[0].name if local_backups else None

    return {
        "status": "success",
        "has_credentials": has_creds,
        "has_client_secret": has_client_secret,
        "connected": config.get("enabled", False),
        "account_email": config.get("account_email"),
        "auth_type": config.get("auth_type"),
        "folder_name": config.get("folder_name", "HouseholdAccountBook_Backups"),
        "folder_id": config.get("folder_id"),
        "warning": config.get("warning"),
        "schedule": config.get("schedule", "off"),
        "last_backup_time": config.get("last_backup_time"),
        "last_backup_status": config.get("last_backup_status"),
        "local_backup_count": local_backup_count,
        "last_local_backup": last_local_backup,
    }

@router.post("/test")
def test_connection():
    """Tests connection to Google Drive."""
    result = test_drive_connection()
    return result

@router.post("/credentials")
async def upload_credentials_file(file: UploadFile = File(...)):
    """Uploads service_account.json or client_secret.json file."""
    try:
        content = await file.read()
        creds_data = json.loads(content.decode("utf-8"))
        result = save_credentials(creds_data)
        return {
            "status": "success",
            "message": result.get("message", "인증 파일이 성공적으로 등록되었습니다."),
            "test_result": result
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="유효한 JSON 파일이 아닙니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"인증 파일 저장 실패: {str(e)}")

@router.post("/oauth/client-secrets")
def configure_oauth_client(body: OAuthClientRequest):
    """Sets OAuth 2.0 client ID and client secret."""
    try:
        res = save_oauth_client_config({
            "client_id": body.client_id,
            "client_secret": body.client_secret
        })
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/oauth/url")
def get_oauth_url(request: Request, redirect_uri: Optional[str] = Query(None)):
    """Returns Google OAuth 2.0 consent authorization URL."""
    try:
        if not redirect_uri:
            redirect_uri = f"{str(request.base_url).rstrip('/')}/api/gdrive/oauth/callback"
        auth_url = get_oauth_authorization_url(redirect_uri)
        return {
            "status": "success",
            "url": auth_url,
            "redirect_uri": redirect_uri
        }
    except FileNotFoundError as fe:
        raise HTTPException(status_code=400, detail=str(fe))
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth URL 생성 실패: {str(e)}")

@router.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Handles Google OAuth 2.0 redirect callback."""
    if error:
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;text-align:center;">
            <h2 style="color:#e11d48;">Google 인증 실패</h2>
            <p>{error}</p>
            <p>창을 닫고 다시 시도해주세요.</p>
            </body></html>""",
            status_code=400
        )
    if not code:
        return HTMLResponse(
            """<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;text-align:center;">
            <h2 style="color:#e11d48;">인증 코드가 전달되지 않았습니다.</h2>
            </body></html>""",
            status_code=400
        )

    redirect_uri = str(request.url).split("?")[0]
    try:
        result = complete_oauth_flow(code, redirect_uri, state=state)
        email = result.get("email", "사용자")
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Google Drive 연동 완료</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      background: #f8fafc;
      color: #1e293b;
    }}
    .card {{
      background: white;
      padding: 2.5rem;
      border-radius: 1.25rem;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
      text-align: center;
      max-width: 440px;
      margin: 1rem;
    }}
    .icon {{ font-size: 3rem; margin-bottom: 0.75rem; }}
    h2 {{ color: #4338ca; margin: 0 0 0.5rem 0; font-size: 1.4rem; font-weight: 800; }}
    p {{ color: #64748b; font-size: 0.95rem; margin: 0.5rem 0 1.25rem 0; line-height: 1.5; }}
    .email {{ font-weight: bold; color: #1e1b4b; background: #e0e7ff; padding: 0.25rem 0.75rem; border-radius: 9999px; display: inline-block; word-break: break-all; }}
    .btn {{
      display: inline-block;
      padding: 0.65rem 1.5rem;
      background: #4f46e5;
      color: white;
      border-radius: 0.75rem;
      text-decoration: none;
      font-weight: bold;
      font-size: 0.9rem;
      cursor: pointer;
      border: none;
      transition: background 0.2s;
    }}
    .btn:hover {{ background: #4338ca; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">☁️🎉</div>
    <h2>Google Drive 연동 성공!</h2>
    <p><span class="email">{email}</span> 계정과 안전하게 연결되었습니다.</p>
    <p style="font-size: 0.85rem;">잠시 후 창이 자동으로 닫히며 가계부 화면이 갱신됩니다.</p>
    <button class="btn" onclick="finish()">창 닫기</button>
  </div>
  <script>
    function finish() {{
      if (window.opener) {{
        try {{
          if (window.opener.loadGdriveStatus) window.opener.loadGdriveStatus();
          if (window.opener.loadGdriveBackupsList) window.opener.loadGdriveBackupsList();
        }} catch(e) {{}}
        window.close();
      }} else {{
        window.location.href = '/';
      }}
    }}
    setTimeout(finish, 1800);
  </script>
</body>
</html>"""
        return HTMLResponse(html_content)
    except Exception as e:
        logger.error(f"OAuth callback exchange failed: {e}")
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;text-align:center;">
            <h2 style="color:#e11d48;">인증 토큰 교환 실패</h2>
            <p>{str(e)}</p>
            <p>창을 닫고 다시 시도해주세요.</p>
            </body></html>""",
            status_code=500
        )

@router.post("/oauth/code")
def submit_oauth_code(body: OAuthCodeRequest, request: Request):
    """Manually completes OAuth flow with authorization code."""
    try:
        redirect_uri = body.redirect_uri or f"{str(request.base_url).rstrip('/')}/api/gdrive/oauth/callback"
        result = complete_oauth_flow(body.code.strip(), redirect_uri, state=body.state)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"인증 코드 교환 실패: {str(e)}")

@router.post("/disconnect")
def disconnect():
    """Disconnects Google Drive and resets credentials."""
    return disconnect_drive()

@router.post("/folder-id")
def update_folder_id(body: FolderIdRequest):
    """Updates custom backup folder ID."""
    return set_backup_folder_id(body.folder_id)

@router.post("/backup")
def trigger_backup():
    """Immediately takes a snapshot and uploads to Google Drive."""
    try:
        res = upload_backup_to_drive()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"구글 드라이브 백업 실패: {str(e)}")

@router.get("/backups")
def get_drive_backups():
    """Lists files saved in Google Drive backup folder."""
    try:
        backups = list_drive_backups()
        return {"status": "success", "backups": backups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백업 목록 조회 실패: {str(e)}")

@router.delete("/backups/{file_id}")
def delete_backup(file_id: str):
    """Deletes specified file from Google Drive."""
    try:
        res = delete_drive_backup(file_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백업 삭제 실패: {str(e)}")

@router.post("/restore/{file_id}")
def restore_backup(file_id: str):
    """Restores database from specified Google Drive file."""
    try:
        res = restore_from_drive_backup(file_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"복원 실패: {str(e)}")

@router.post("/schedule")
def set_schedule(body: ScheduleUpdateRequest):
    """Updates automatic periodic backup schedule."""
    try:
        res = update_backup_schedule(body.schedule)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/local-backups")
def list_local_backups():
    """Lists local backup snapshots on the server."""
    files = sorted(BACKUP_DIR.glob("account_book_*.db"), reverse=True)
    items = []
    for f in files:
        items.append({
            "name": f.name,
            "size": f.stat().st_size,
            "modified_time": f.stat().st_mtime
        })
    return {"status": "success", "backups": items}
