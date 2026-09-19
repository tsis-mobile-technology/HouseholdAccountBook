import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.gdrive_service import (
    load_gdrive_config,
    test_drive_connection,
    save_credentials,
    upload_backup_to_drive,
    list_drive_backups,
    restore_from_drive_backup,
    update_backup_schedule,
    GDRIVE_CREDS_FILE,
)
from app.core.config import BACKUP_DIR

router = APIRouter(prefix="/api/gdrive", tags=["Google Drive"])

class ScheduleUpdateRequest(BaseModel):
    schedule: str  # off, daily, weekly, monthly

@router.get("/status")
def get_status():
    config = load_gdrive_config()
    has_creds = GDRIVE_CREDS_FILE.exists()

    # Count local backups
    local_backups = sorted(BACKUP_DIR.glob("account_book_*.db"), reverse=True)
    local_backup_count = len(local_backups)
    last_local_backup = local_backups[0].name if local_backups else None

    return {
        "status": "success",
        "has_credentials": has_creds,
        "connected": config.get("enabled", False),
        "account_email": config.get("account_email"),
        "auth_type": config.get("auth_type"),
        "folder_name": config.get("folder_name", "HouseholdAccountBook_Backups"),
        "schedule": config.get("schedule", "off"),
        "last_backup_time": config.get("last_backup_time"),
        "last_backup_status": config.get("last_backup_status"),
        "local_backup_count": local_backup_count,
        "last_local_backup": last_local_backup,
    }

@router.post("/test")
def test_connection():
    result = test_drive_connection()
    return result

@router.post("/credentials")
async def upload_credentials_file(file: UploadFile = File(...)):
    """Uploads service_account.json credentials file."""
    try:
        content = await file.read()
        creds_data = json.loads(content.decode("utf-8"))
        result = save_credentials(creds_data)
        return {
            "status": "success",
            "message": "인증 파일이 성공적으로 등록되었습니다.",
            "test_result": result
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="유효한 JSON 파일이 아닙니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"인증 파일 저장 실패: {str(e)}")

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
