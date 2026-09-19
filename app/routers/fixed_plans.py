from typing import Dict, List
from fastapi import APIRouter, Query
from app.models.schemas import FixedPlanItem, MonthFixedPlansUpdate
from app.services.fixed_plan_service import get_month_fixed_plans, save_month_fixed_plans

router = APIRouter(prefix="/api/fixed-plans", tags=["Fixed Plans"])

@router.get("/{year}/{month}", response_model=Dict[str, List[FixedPlanItem]])
def get_plans(year: int, month: int):
    return get_month_fixed_plans(year, month)

@router.post("/{year}/{month}", response_model=dict)
@router.put("/{year}/{month}", response_model=dict)
def save_plans(
    year: int,
    month: int,
    payload: MonthFixedPlansUpdate,
    set_as_template: bool = Query(False)
):
    is_template_flag = payload.is_template if payload.is_template is not None else bool(set_as_template)
    save_month_fixed_plans(
        year=year,
        month=month,
        incomes=payload.incomes,
        expenses=payload.expenses,
        savings=payload.savings,
        set_as_default_template=is_template_flag
    )
    return {"status": "success", "message": "고정 계획이 저장되었습니다."}
