from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from app.models.schemas import CardPreviewResponse, CardConfirmRequest, CardConfirmResponse
from app.services.card_statement_service import (
    auto_detect_and_parse,
    enrich_and_detect_duplicates,
    get_payment_method_id_by_name,
    execute_card_import,
)

router = APIRouter(prefix="/api/cards", tags=["Cards"])

@router.post("/preview", response_model=CardPreviewResponse)
async def preview_card_statement(
    file: UploadFile = File(...),
    target_year: Optional[int] = Form(None),
    target_month: Optional[int] = Form(None),
):
    """
    Receives Samsung, Shinhan, or Hyundai card statement file (.xlsx, .xls),
    auto-detects the issuer, extracts all transactions (including installments & refunds),
    auto-classifies categories, and runs duplicate checks against existing manual records.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="업로드된 파일이 비어 있습니다.")

    try:
        issuer_key, issuer_name, statement_month, raw_items = auto_detect_and_parse(content, file.filename or "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"카드 명세서 분석 실패: {str(e)}")

    if not raw_items:
        raise HTTPException(status_code=400, detail="명세서에서 승인 및 청구 내역을 찾을 수 없습니다.")

    # Override statement_month if user provided target_year and target_month
    if target_year and target_month:
        statement_month = f"{target_year:04d}-{target_month:02d}"

    payment_method_id = get_payment_method_id_by_name(issuer_name)
    enriched_items = enrich_and_detect_duplicates(raw_items, issuer_name, payment_method_id)

    total_amount = sum(it.amount for it in enriched_items)
    duplicate_count = sum(1 for it in enriched_items if it.is_duplicate)

    return CardPreviewResponse(
        issuer=issuer_key,
        issuer_name=issuer_name,
        filename=file.filename or "",
        statement_month=statement_month or "",
        total_count=len(enriched_items),
        total_amount=total_amount,
        duplicate_count=duplicate_count,
        items=enriched_items,
    )

@router.post("/confirm", response_model=CardConfirmResponse)
def confirm_card_import(req: CardConfirmRequest):
    """
    Applies user-selected actions (add_new, merge, skip) to the database.
    """
    if not req.items:
        return CardConfirmResponse(
            status="success",
            added=0,
            merged=0,
            skipped=0,
            total=0,
            message="반영할 항목이 없습니다."
        )

    return execute_card_import(req.items)
