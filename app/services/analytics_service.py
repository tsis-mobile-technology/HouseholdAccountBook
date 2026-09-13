from typing import Dict, List, Any
from app.database.connection import get_connection
from app.models.schemas import MonthlySummaryResponse, AnnualMonthRow, AnnualDashboardResponse
from app.services.fixed_plan_service import get_month_fixed_plans

def get_monthly_summary(year: int, month: int) -> MonthlySummaryResponse:
    # 1. Fixed plans
    plans = get_month_fixed_plans(year, month)
    total_income = sum(i.amount for i in plans["incomes"])
    fixed_expense = sum(e.amount for e in plans["expenses"])
    savings_investment = sum(s.amount for s in plans["savings"])

    # 2. Variable expenses
    prefix = f"{year:04d}-{month:02d}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as var_sum
            FROM variable_expenses
            WHERE transaction_date LIKE ?
        """, (prefix,))
        row = cur.fetchone()
        variable_expense = row["var_sum"] if row else 0
    finally:
        conn.close()

    total_expense = fixed_expense + variable_expense
    balance = total_income - total_expense - savings_investment
    savings_rate = round((savings_investment / total_income * 100), 1) if total_income > 0 else 0.0

    return MonthlySummaryResponse(
        year=year,
        month=month,
        total_income=total_income,
        fixed_expense=fixed_expense,
        variable_expense=variable_expense,
        total_expense=total_expense,
        savings_investment=savings_investment,
        balance=balance,
        savings_rate=savings_rate
    )

def get_annual_dashboard(year: int) -> AnnualDashboardResponse:
    month_rows: List[AnnualMonthRow] = []

    # Compute for each month 1..12
    for m in range(1, 13):
        summary = get_monthly_summary(year, m)
        month_rows.append(AnnualMonthRow(
            month=m,
            month_name=f"{m}월",
            total_income=summary.total_income,
            fixed_expense=summary.fixed_expense,
            variable_expense=summary.variable_expense,
            total_expense=summary.total_expense,
            savings_investment=summary.savings_investment,
            balance=summary.balance,
            savings_rate=summary.savings_rate
        ))

    # Annual Total
    ann_income = sum(r.total_income for r in month_rows)
    ann_fixed = sum(r.fixed_expense for r in month_rows)
    ann_var = sum(r.variable_expense for r in month_rows)
    ann_expense = sum(r.total_expense for r in month_rows)
    ann_savings = sum(r.savings_investment for r in month_rows)
    ann_balance = sum(r.balance for r in month_rows)
    ann_rate = round((ann_savings / ann_income * 100), 1) if ann_income > 0 else 0.0

    annual_total = AnnualMonthRow(
        month=0,
        month_name="연간 합계",
        total_income=ann_income,
        fixed_expense=ann_fixed,
        variable_expense=ann_var,
        total_expense=ann_expense,
        savings_investment=ann_savings,
        balance=ann_balance,
        savings_rate=ann_rate
    )

    # Monthly Average
    avg_income = int(round(ann_income / 12))
    avg_fixed = int(round(ann_fixed / 12))
    avg_var = int(round(ann_var / 12))
    avg_expense = int(round(ann_expense / 12))
    avg_savings = int(round(ann_savings / 12))
    avg_balance = int(round(ann_balance / 12))
    avg_rate = ann_rate

    monthly_average = AnnualMonthRow(
        month=0,
        month_name="월평균",
        total_income=avg_income,
        fixed_expense=avg_fixed,
        variable_expense=avg_var,
        total_expense=avg_expense,
        savings_investment=avg_savings,
        balance=avg_balance,
        savings_rate=avg_rate
    )

    return AnnualDashboardResponse(
        year=year,
        months=month_rows,
        annual_total=annual_total,
        monthly_average=monthly_average
    )

def get_category_breakdown(year: int, month: int) -> List[Dict[str, Any]]:
    """Returns category breakdown for a given year & month for donut charts."""
    prefix = f"{year:04d}-{month:02d}%"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.name, c.color_hex, c.icon, COALESCE(SUM(v.amount), 0) as total_amount
            FROM categories c
            LEFT JOIN variable_expenses v ON c.id = v.category_id AND v.transaction_date LIKE ?
            WHERE c.is_active = 1
            GROUP BY c.id
            HAVING total_amount > 0
            ORDER BY total_amount DESC
        """, (prefix,))
        rows = cur.fetchall()
        total_sum = sum(r["total_amount"] for r in rows)
        result = []
        for r in rows:
            pct = round((r["total_amount"] / total_sum * 100), 1) if total_sum > 0 else 0.0
            result.append({
                "category_id": r["id"],
                "name": r["name"],
                "color_hex": r["color_hex"],
                "icon": r["icon"],
                "amount": r["total_amount"],
                "percentage": pct
            })
        return result
    finally:
        conn.close()
