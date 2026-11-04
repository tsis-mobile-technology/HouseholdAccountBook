from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query
from app.models.schemas import MonthlySummaryResponse, AnnualDashboardResponse, SpendingPatternsResponse
from app.services.analytics_service import (
    get_monthly_summary,
    get_annual_dashboard,
    get_category_breakdown,
    get_spending_pattern_analytics,
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

@router.get("/spending-patterns", response_model=SpendingPatternsResponse)
def read_spending_patterns(
    year: int = Query(..., description="연도"),
    month: int = Query(..., ge=1, le=12, description="월")
):
    return get_spending_pattern_analytics(year, month)

@router.get("/spending-patterns/{year}/{month}", response_model=SpendingPatternsResponse)
def read_spending_patterns_path(year: int, month: int):
    return get_spending_pattern_analytics(year, month)

