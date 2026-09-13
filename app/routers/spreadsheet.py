from fastapi import APIRouter, UploadFile, File, Response, HTTPException
from fastapi.responses import StreamingResponse
import io
import json
from urllib.parse import quote
from app.services.spreadsheet_service import (
    export_to_excel_bytes,
    import_from_excel_file,
    export_all_json,
    restore_all_json
)

router = APIRouter(prefix="/api/spreadsheet", tags=["Spreadsheet"])

@router.get("/export/{year}")
def export_excel(year: int):
    file_bytes = export_to_excel_bytes(year)
    raw_filename = f"가계부_{year}년.xlsx"
    encoded_filename = quote(raw_filename)
    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

@router.post("/import")
async def import_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="XLSX 엑셀 파일만 업로드할 수 있습니다.")
    contents = await file.read()
    try:
        counts = import_from_excel_file(contents)
        return {
            "status": "success",
            "message": "스프레드시트 데이터를 성공적으로 가져왔습니다.",
            "imported": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가져오기 중 오류 발생: {str(e)}")

@router.get("/backup-json")
def backup_json():
    data = export_all_json()
    content = json.dumps(data, ensure_ascii=False, indent=2)
    filename = f"household_account_backup_{data.get('exported_at', 'full')}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/restore-json")
async def restore_json(file: UploadFile = File(...)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON 백업 파일만 업로드할 수 있습니다.")
    contents = await file.read()
    try:
        data = json.loads(contents.decode("utf-8"))
        restore_all_json(data)
        return {"status": "success", "message": "데이터가 성공적으로 복원되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"복원 실패: {str(e)}")

from pydantic import BaseModel

class ResetRequest(BaseModel):
    confirm_text: str

@router.post("/reset")
def reset_database(payload: ResetRequest):
    if payload.confirm_text.strip() != "초기화":
        raise HTTPException(status_code=400, detail="초기화를 진행하려면 '초기화'를 정확히 입력해야 합니다.")
    from app.services.spreadsheet_service import reset_all_data
    backup_name = reset_all_data(keep_default_templates=True)
    return {
        "status": "success",
        "message": "데이터가 성공적으로 초기화되었습니다.",
        "backup_file": backup_name
    }

@router.post("/load-sample")
def load_sample_data():
    from app.services.spreadsheet_service import load_sample_template_data
    counts = load_sample_template_data()
    return {
        "status": "success",
        "message": "구글 스프레드시트 예시 데이터를 로드했습니다.",
        "imported": counts
    }


