from typing import List, Dict, Any
from fastapi import APIRouter
from app.models.schemas import MonthlySummaryResponse, AnnualDashboardResponse
from app.services.analytics_service import (
    get_monthly_summary,
    get_annual_dashboard,
    get_category_breakdown
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/monthly/{year}/{month}", response_model=MonthlySummaryResponse)
def read_monthly_summary(year: int, month: int):
    return get_monthly_summary(year, month)

@router.get("/annual/{year}", response_model=AnnualDashboardResponse)
def read_annual_dashboard(year: int):
    return get_annual_dashboard(year)

@router.get("/categories/{year}/{month}", response_model=List[Dict[str, Any]])
def read_category_breakdown(year: int, month: int):
    return get_category_breakdown(year, month)
