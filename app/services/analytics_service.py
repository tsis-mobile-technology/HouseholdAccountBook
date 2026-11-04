import calendar
import re
from datetime import datetime
from typing import Dict, List, Any
from app.database.connection import get_connection
from app.models.schemas import (
    MonthlySummaryResponse,
    AnnualMonthRow,
    AnnualDashboardResponse,
    CategorySpendingItem,
    PaymentMethodSpendingItem,
    WeeklySpendingItem,
    DayOfWeekSpendingItem,
    TopMerchantItem,
    SpendingPatternsResponse,
)
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


def get_spending_pattern_analytics(year: int, month: int) -> SpendingPatternsResponse:
    """
    Computes comprehensive monthly spending pattern analytics:
      - KPI metrics & MoM change
      - Category breakdown with MoM growth comparison
      - Payment method / Card issuer breakdown
      - Weekly & day-of-week spending rhythms (including weekday vs weekend)
      - Top 10 merchants ranking
      - Auto-generated insight summary
    """
    prefix = f"{year:04d}-{month:02d}%"
    prev_year = year if month > 1 else year - 1
    prev_month = month - 1 if month > 1 else 12
    prev_prefix = f"{prev_year:04d}-{prev_month:02d}%"

    days_in_month = calendar.monthrange(year, month)[1]

    conn = get_connection()
    try:
        cur = conn.cursor()

        # 1. Fetch all transactions for this month
        cur.execute("""
            SELECT v.id, v.transaction_date, v.category_id, c.name as category_name,
                   c.color_hex, c.icon, v.payment_method_id, p.name as payment_method_name,
                   v.title, v.amount, v.memo
            FROM variable_expenses v
            JOIN categories c ON v.category_id = c.id
            JOIN payment_methods p ON v.payment_method_id = p.id
            WHERE v.transaction_date LIKE ?
            ORDER BY v.transaction_date ASC, v.id ASC
        """, (prefix,))
        rows = [dict(r) for r in cur.fetchall()]

        # 2. Fetch previous month category sums
        cur.execute("""
            SELECT v.category_id, COALESCE(SUM(v.amount), 0) as cat_sum
            FROM variable_expenses v
            WHERE v.transaction_date LIKE ?
            GROUP BY v.category_id
        """, (prev_prefix,))
        prev_cat_rows = {r["category_id"]: r["cat_sum"] for r in cur.fetchall()}

        # Previous month total spending
        cur.execute("""
            SELECT COALESCE(SUM(v.amount), 0) as tot_sum
            FROM variable_expenses v
            WHERE v.transaction_date LIKE ?
        """, (prev_prefix,))
        prev_total_row = cur.fetchone()
        prev_total_spending = prev_total_row["tot_sum"] if prev_total_row else 0

        # All categories metadata
        cur.execute("SELECT id, name, color_hex, icon FROM categories WHERE is_active = 1")
        all_categories = {r["id"]: dict(r) for r in cur.fetchall()}

        # All payment methods
        cur.execute("SELECT id, name FROM payment_methods WHERE is_active = 1")
        all_payments = {r["id"]: r["name"] for r in cur.fetchall()}

    finally:
        conn.close()

    total_spending = sum(r["amount"] for r in rows)
    spending_diff = total_spending - prev_total_spending
    spending_diff_rate = round((spending_diff / prev_total_spending * 100), 1) if prev_total_spending > 0 else 0.0

    tx_count = len(rows)
    daily_average = int(round(total_spending / days_in_month)) if days_in_month > 0 else 0
    avg_per_tx = int(round(total_spending / tx_count)) if tx_count > 0 else 0

    # Distinct spend days
    spend_dates = {r["transaction_date"] for r in rows if r["amount"] > 0}
    no_spend_days = max(0, days_in_month - len(spend_dates))

    # Peak spend date
    date_sums: Dict[str, int] = {}
    for r in rows:
        d = r["transaction_date"]
        date_sums[d] = date_sums.get(d, 0) + r["amount"]

    peak_date = None
    peak_amt = 0
    if date_sums:
        peak_date, peak_amt = max(date_sums.items(), key=lambda x: x[1])

    # 3. Category Breakdown & MoM comparison
    cat_items_map: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        cat_items_map.setdefault(r["category_id"], []).append(r)

    categories_result: List[CategorySpendingItem] = []
    # Include all categories that had spending this month or previous month
    relevant_cat_ids = set(cat_items_map.keys()) | set(prev_cat_rows.keys())

    for cid in relevant_cat_ids:
        c_meta = all_categories.get(cid, {"name": "기타", "color_hex": "#E2E8F0", "icon": "ellipsis-h"})
        c_rows = cat_items_map.get(cid, [])
        c_amt = sum(r["amount"] for r in c_rows)
        c_prev = prev_cat_rows.get(cid, 0)
        c_diff = c_amt - c_prev
        c_diff_rate = round((c_diff / c_prev * 100), 1) if c_prev > 0 else (100.0 if c_amt > 0 else 0.0)
        c_pct = round((c_amt / total_spending * 100), 1) if total_spending > 0 else 0.0

        if c_amt != 0 or c_prev != 0:
            categories_result.append(CategorySpendingItem(
                category_id=cid,
                name=c_meta["name"],
                color_hex=c_meta["color_hex"],
                icon=c_meta["icon"],
                amount=c_amt,
                percentage=c_pct,
                prev_amount=c_prev,
                diff_amount=c_diff,
                diff_rate=c_diff_rate,
                count=len(c_rows),
            ))

    # Sort categories by amount descending
    categories_result.sort(key=lambda x: x.amount, reverse=True)

    # 4. Payment Method / Card Issuer Breakdown
    pm_sums: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        pid = r["payment_method_id"]
        pname = r["payment_method_name"]
        if pid not in pm_sums:
            pm_sums[pid] = {"id": pid, "name": pname, "amount": 0, "count": 0}
        pm_sums[pid]["amount"] += r["amount"]
        pm_sums[pid]["count"] += 1

    payment_result: List[PaymentMethodSpendingItem] = []
    for pid, pdata in sorted(pm_sums.items(), key=lambda x: x[1]["amount"], reverse=True):
        p_pct = round((pdata["amount"] / total_spending * 100), 1) if total_spending > 0 else 0.0
        payment_result.append(PaymentMethodSpendingItem(
            payment_method_id=pid,
            name=pdata["name"],
            amount=pdata["amount"],
            count=pdata["count"],
            percentage=p_pct,
        ))

    # 5. Weekly Spending Rhythm (1주차: 1~7일, 2주차: 8~14일, 3주차: 15~21일, 4주차: 22~28일, 5주차: 29~31일)
    weeks_def = [
        (1, f"1주차 (1일~7일)", 1, 7),
        (2, f"2주차 (8일~14일)", 8, 14),
        (3, f"3주차 (15일~21일)", 15, 21),
        (4, f"4주차 (22일~28일)", 22, 28),
        (5, f"5주차 (29일~{days_in_month}일)", 29, days_in_month),
    ]

    weekly_result: List[WeeklySpendingItem] = []
    for w_num, w_label, start_d, end_d in weeks_def:
        w_rows = [
            r for r in rows
            if start_d <= int(r["transaction_date"].split("-")[2]) <= end_d
        ]
        w_amt = sum(r["amount"] for r in w_rows)
        weekly_result.append(WeeklySpendingItem(
            week_num=w_num,
            week_label=w_label,
            amount=w_amt,
            count=len(w_rows),
        ))

    # 6. Day of Week & Weekday vs Weekend
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    dow_sums = {i: {"amount": 0, "count": 0} for i in range(7)}

    weekday_total = 0
    weekend_total = 0

    for r in rows:
        try:
            dt = datetime.strptime(r["transaction_date"], "%Y-%m-%d")
            wday = dt.weekday()  # 0=Mon..6=Sun
            dow_sums[wday]["amount"] += r["amount"]
            dow_sums[wday]["count"] += 1
            if wday < 5:
                weekday_total += r["amount"]
            else:
                weekend_total += r["amount"]
        except Exception:
            continue

    # Count actual weekdays vs weekend days in this month
    weekday_days_count = 0
    weekend_days_count = 0
    for day_i in range(1, days_in_month + 1):
        try:
            d_obj = datetime(year, month, day_i)
            if d_obj.weekday() < 5:
                weekday_days_count += 1
            else:
                weekend_days_count += 1
        except Exception:
            pass

    weekday_avg = int(round(weekday_total / weekday_days_count)) if weekday_days_count > 0 else 0
    weekend_avg = int(round(weekend_total / weekend_days_count)) if weekend_days_count > 0 else 0

    dow_result: List[DayOfWeekSpendingItem] = [
        DayOfWeekSpendingItem(
            day_name=day_names[i],
            amount=dow_sums[i]["amount"],
            count=dow_sums[i]["count"]
        )
        for i in range(7)
    ]

    # 7. Top 10 Merchants
    merch_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        clean_title = re.sub(r"\[할부.*?\]|\[취소.*?\]", "", r["title"]).strip()
        if not clean_title:
            clean_title = r["title"]
        if clean_title not in merch_map:
            merch_map[clean_title] = {
                "merchant": clean_title,
                "amount": 0,
                "count": 0,
                "category_name": r["category_name"],
            }
        merch_map[clean_title]["amount"] += r["amount"]
        merch_map[clean_title]["count"] += 1

    top_merchants_list: List[TopMerchantItem] = []
    sorted_merchs = sorted(merch_map.values(), key=lambda x: x["amount"], reverse=True)
    for rank, m_item in enumerate(sorted_merchs[:10], start=1):
        m_pct = round((m_item["amount"] / total_spending * 100), 1) if total_spending > 0 else 0.0
        top_merchants_list.append(TopMerchantItem(
            rank=rank,
            merchant=m_item["merchant"],
            amount=m_item["amount"],
            count=m_item["count"],
            percentage=m_pct,
            category_name=m_item["category_name"],
        ))

    # 8. AI-Style Insight Summary Synthesis
    insight_parts = []
    if categories_result:
        top_cat = categories_result[0]
        insight_parts.append(f"이번 달 최대 소비 영역은 '{top_cat.name}'(으)로 총 {top_cat.amount:,}원({top_cat.percentage}%)을 지출했습니다.")

    if spending_diff != 0 and prev_total_spending > 0:
        if spending_diff > 0:
            insight_parts.append(f"전월 대비 지출이 {spending_diff:,}원(+{spending_diff_rate}%) 증가했습니다.")
        else:
            insight_parts.append(f"전월 대비 지출이 {abs(spending_diff):,}원({spending_diff_rate}%) 감소하여 절약을 실천했습니다.")

    if weekend_avg > 0 and weekday_avg > 0:
        ratio = round(weekend_avg / weekday_avg, 1)
        if ratio >= 1.5:
            insight_parts.append(f"주말 일평균 지출({weekend_avg:,}원)이 평일({weekday_avg:,}원)보다 {ratio}배 높아 주말 집중 소비 패턴을 보입니다.")
        elif ratio <= 0.7:
            insight_parts.append(f"평일 일평균 지출({weekday_avg:,}원)이 주말({weekend_avg:,}원)보다 높아 평일 활동 중심의 소비를 나타냅니다.")

    if no_spend_days > 0:
        insight_parts.append(f"한 달 중 {no_spend_days}일의 '무지출 데이'를 달성했습니다.")

    insight_summary = " ".join(insight_parts) if insight_parts else "등록된 지출 내역을 바탕으로 소비 패턴을 분석합니다."

    return SpendingPatternsResponse(
        year=year,
        month=month,
        total_spending=total_spending,
        prev_total_spending=prev_total_spending,
        spending_diff=spending_diff,
        spending_diff_rate=spending_diff_rate,
        daily_average=daily_average,
        transaction_count=tx_count,
        avg_per_transaction=avg_per_tx,
        no_spend_days=no_spend_days,
        peak_spending_date=peak_date,
        peak_spending_amount=peak_amt,
        weekday_spending=weekday_total,
        weekend_spending=weekend_total,
        weekday_avg=weekday_avg,
        weekend_avg=weekend_avg,
        insight_summary=insight_summary,
        categories=categories_result,
        payment_methods=payment_result,
        weekly=weekly_result,
        day_of_week=dow_result,
        top_merchants=top_merchants_list,
    )
