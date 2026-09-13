from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    VariableExpenseCreate,
    VariableExpenseUpdate,
    VariableExpenseResponse,
    MobileOverviewResponse,
)
from app.services.transaction_service import (
    create_variable_expense,
    update_variable_expense,
    delete_variable_expense,
    get_variable_expenses,
    get_today_summary,
)
from app.services.analytics_service import get_monthly_summary

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.post("", response_model=dict)
def add_transaction(item: VariableExpenseCreate):
    new_id = create_variable_expense(item)
    return {"status": "success", "id": new_id, "message": "지출 내역이 등록되었습니다."}

@router.get("", response_model=List[VariableExpenseResponse])
def list_transactions(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    limit: int = Query(500, le=2000)
):
    return get_variable_expenses(
        year=year,
        month=month,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        limit=limit
    )

@router.put("/{expense_id}", response_model=dict)
def modify_transaction(expense_id: int, item: VariableExpenseUpdate):
    ok = update_variable_expense(expense_id, item)
    if not ok:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없거나 변경 사항이 없습니다.")
    return {"status": "success", "message": "수정되었습니다."}

@router.delete("/{expense_id}", response_model=dict)
def remove_transaction(expense_id: int):
    ok = delete_variable_expense(expense_id)
    if not ok:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
    return {"status": "success", "message": "삭제되었습니다."}

@router.get("/overview", response_model=MobileOverviewResponse)
def get_mobile_overview():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_amt, today_cnt = get_today_summary(today_str)
    month_sum = get_monthly_summary(now.year, now.month)
    recents = get_variable_expenses(start_date=today_str, end_date=today_str, limit=20)

    return MobileOverviewResponse(
        today_date=today_str,
        today_expense_total=today_amt,
        today_transaction_count=today_cnt,
        month_summary=month_sum,
        recent_transactions=recents
    )
