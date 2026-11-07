import calendar
import re
from datetime import datetime
from typing import Dict, List, Any
from app.database.connection import get_connection
from app.models.schemas import (
    MonthlySummaryResponse,
    AnnualMonthRow,
    AnnualDashboardResponse,
    CategorySubItem,
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


def clean_merchant_name(raw_title: str) -> str:
    """Cleans installment tags, corporate prefixes, and normalizes brand names."""
    if not raw_title:
        return "기타"
    # 1. Strip installment/cancel brackets
    title = re.sub(r"\[할부.*?\]|\[취소.*?\]", "", raw_title).strip()
    if not title:
        title = raw_title.strip()

    # 2. Strip corporate prefixes & suffixes
    title = re.sub(r"^\(주\)|\(주\)$|^주식회사\s*|\s*주식회사|^㈜|㈜$|^\(유\)|\(유\)$|^유한회사\s*|\s*유한회사", "", title).strip()

    # 3. Known brand normalization
    t_lower = title.lower()
    if "우아한형제들" in title or "배달의민족" in title or "배민" in title:
        return "배달의민족"
    if "코스트코" in title:
        return "코스트코"
    if "이마트" in title and "24" not in title:
        return "이마트"
    if "쿠팡" in title:
        return "쿠팡"
    if "다이소" in title:
        return "다이소"
    if "올리브영" in title:
        return "올리브영"
    if "네이버" in title:
        return "네이버페이"
    if "아이파크" in title:
        return "고척아이파크몰"
    if "지에스칼텍스" in title or "gs칼텍스" in t_lower:
        return "GS칼텍스 주유소"
    if "철도승차권" in title or "코레일" in title or "ktx" in t_lower:
        return "코레일(KTX/철도)"
    if "알앤알" in title:
        return "알앤알에듀"
    if "사과나무" in title:
        return "사과나무학원"
    if "시대인재" in title or "하이컨시" in title:
        return "시대인재"
    if "러셀" in title:
        return "러셀학원"
    if "펫프렌즈" in title:
        return "펫프렌즈"
    if "넷플릭스" in title:
        return "넷플릭스"
    if "cgv" in t_lower:
        return "CGV"
    if "ssg.com" in t_lower or "쓱닷컴" in title:
        return "SSG.COM"
    if "무신사" in title:
        return "무신사"
    if "아웃백" in title:
        return "아웃백"
    if "남시약국" in title:
        return "남시약국"
    if "뽀빠이마취" in title:
        return "뽀빠이마취통증의학과"
    if "이화여자고등" in title:
        if "조식" in title: return "이화여고 조식비"
        if "중식" in title: return "이화여고 중식비"
        if "석식" in title: return "이화여고 석식비"
        if "수학여행" in title: return "이화여고 수학여행비"
        return "이화여고 학교납입금"

    return title


def classify_sub_category(cat_name: str, clean_name: str, raw_title: str) -> str:
    """Classifies transaction into a high-level sub-category based on category and title keywords."""
    t = f"{clean_name} {raw_title}".lower()

    if cat_name == "식비":
        if any(k in t for k in ["코스트코", "이마트", "홈플러스", "롯데마트", "트레이더스", "하나로", "장보기"]):
            return "대형마트 / 장보기"
        if any(k in t for k in ["쿠팡", "컬리", "오아시스", "쓱닷컴", "ssg"]):
            return "온라인 장보기 / e커머스"
        if any(k in t for k in ["마트", "슈퍼", "상회", "유통", "청과", "정육", "시장", "농협"]):
            return "동네슈퍼 / 로컬마트"
        if any(k in t for k in ["과일", "채소", "고구마", "무화과", "사과", "정육", "반찬", "떡"]):
            return "신선식품 / 과일"
        return "기타 식비"

    elif cat_name == "외식/카페":
        if any(k in t for k in ["우아한형제들", "배달의민족", "배민", "요기요", "쿠팡이츠"]):
            return "배달음식 / 배민"
        if any(k in t for k in ["카페", "커피", "투썸", "스타벅스", "폴바셋", "이디야", "메가", "베이커리", "빵", "디저트", "공차", "설빙"]):
            return "카페 / 디저트"
        if any(k in t for k in ["맥도날드", "버거", "피자", "치킨", "떡볶이", "분식", "앤티앤스", "엽떡", "짜장", "중화", "탕수육"]):
            return "패스트푸드 / 분식 / 야식"
        if any(k in t for k in ["아웃백", "식당", "갈비", "고기", "숯불", "회", "가족 외식", "송림가", "실크로드", "초밥", "파스타", "레스토랑"]):
            return "일반식당 / 외식"
        return "일반식당 / 외식"

    elif cat_name == "교통/차량":
        if any(k in t for k in ["주유", "칼텍스", "오일", "에너지", "충전", "gs"]):
            return "주유 / 충전"
        if any(k in t for k in ["철도", "코레일", "ktx", "srt", "기차", "승차권", "고속버스", "시외버스", "공항"]):
            return "기차 / 시외교통"
        if any(k in t for k in ["엔진오일", "정비", "공업사", "카센터", "타이어", "수리", "세차"]):
            return "차량정비 / 유지"
        if any(k in t for k in ["버스", "지하철", "교통-", "티머니", "택시", "카카오t"]):
            return "시내대중교통 / 택시"
        return "기타 교통"

    elif cat_name == "학원/도서":
        if any(k in t for k in ["러셀", "알앤알", "사과나무", "시대인재", "학원", "정상제이엘에스", "교육", "보습"]):
            return "학원 수강료"
        if any(k in t for k in ["이화여고", "학교", "조식", "중식", "석식", "급식", "수학여행", "대학교", "원광대"]):
            return "학교납입금 / 급식"
        if any(k in t for k in ["스터디카페", "독서실"]):
            return "스터디카페 / 독서실"
        if any(k in t for k in ["교재", "도서", "교보", "알라딘", "예스24", "서점", "책"]):
            return "도서 / 교재비"
        return "기타 교육"

    elif cat_name == "쇼핑/의류":
        if any(k in t for k in ["ssg", "네이버", "쿠팡", "11번가", "온라인", "플랫폼"]):
            return "온라인 쇼핑몰"
        if any(k in t for k in ["아이파크", "백화점", "아울렛", "몰", "타임스퀘어"]):
            return "백화점 / 복합몰"
        if any(k in t for k in ["옷", "의류", "신발", "운동화", "abc마트", "무신사", "에잇세컨즈", "교복", "캐쥬얼", "패션"]):
            return "의류 / 잡화 / 패션"
        if any(k in t for k in ["올리브영", "화장품", "뷰티"]):
            return "뷰티 / 화장품"
        return "기타 쇼핑"

    elif cat_name == "의료/건강":
        if any(k in t for k in ["약국", "남시약국", "온누리"]):
            return "약국 / 의약품"
        if any(k in t for k in ["병원", "의원", "치과", "내과", "마취", "통증", "한의원", "진료", "메디칼"]):
            return "병의원 / 진료"
        if any(k in t for k in ["안경", "렌즈", "건강식품"]):
            return "안경 / 건강보조"
        return "기타 의료"

    elif cat_name == "생활용품":
        if any(k in t for k in ["다이소", "잡화", "소품", "생필품"]):
            return "생활잡화 / 다이소"
        if any(k in t for k in ["cu", "gs25", "세븐일레븐", "이마트24", "편의점"]):
            return "편의점"
        if any(k in t for k in ["코스트코", "올리브영"]):
            return "마트 / 드럭스토어 생필품"
        return "기타 생활용품"

    elif cat_name == "별콩이":
        if any(k in t for k in ["사료", "간식", "템테이션", "텐더", "북어", "트릿", "치킨"]):
            return "반려묘 사료 / 간식"
        if any(k in t for k in ["병원", "동물병원", "진료"]):
            return "동물병원 / 진료"
        if any(k in t for k in ["펫프렌즈", "장난감", "용품", "모래"]):
            return "반려용품 / 장난감"
        return "기타 반려동물"

    elif cat_name == "문화/여가":
        if any(k in t for k in ["cgv", "시네마", "영화"]):
            return "영화 / 공연"
        if any(k in t for k in ["넷플릭스", "유튜브", "티빙", "ott", "구독"]):
            return "OTT / 디지털구독"
        if any(k in t for k in ["롯데월드", "약속", "인사동", "여행"]):
            return "나들이 / 여가"
        return "기타 여가"

    elif cat_name == "기타":
        if any(k in t for k in ["관리비", "아파트"]):
            return "주거 / 관리비"
        if any(k in t for k in ["시대인재", "학원", "정상제이엘에스"]):
            return "교육 / 학원(미분류)"
        if any(k in t for k in ["공업사", "자동차", "정비"]):
            return "차량유지 / 공업사"
        if any(k in t for k in ["통신", "sk", "kt", "lgu", "브로드밴드"]):
            return "통신비 / 인터넷"
        if any(k in t for k in ["구글", "google", "클라우드", "소프트웨어"]):
            return "디지털 / 클라우드"
        if any(k in t for k in ["안경", "진정성"]):
            return "의료 / 안경"
        if any(k in t for k in ["실크로드", "송림가"]):
            return "외식 / 모임"
        return "일반 기타"

    return "기타"


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

        # 1) Sub-categories (소비 목적/유형별 2Depth)
        sub_items_map: Dict[str, Dict[str, Any]] = {}
        # 2) Merchants (정제된 가맹점/브랜드별 2Depth)
        merchant_items_map: Dict[str, Dict[str, Any]] = {}

        for r in c_rows:
            raw_title = r["title"] or ""
            clean_name = clean_merchant_name(raw_title)
            sub_name = classify_sub_category(c_meta["name"], clean_name, raw_title)

            # Sub-category aggregation
            if sub_name not in sub_items_map:
                sub_items_map[sub_name] = {"name": sub_name, "amount": 0, "count": 0}
            sub_items_map[sub_name]["amount"] += r["amount"]
            sub_items_map[sub_name]["count"] += 1

            # Merchant aggregation
            if clean_name not in merchant_items_map:
                merchant_items_map[clean_name] = {"name": clean_name, "amount": 0, "count": 0}
            merchant_items_map[clean_name]["amount"] += r["amount"]
            merchant_items_map[clean_name]["count"] += 1

        sorted_subs = sorted(sub_items_map.values(), key=lambda x: x["amount"], reverse=True)
        sub_items_list: List[CategorySubItem] = [
            CategorySubItem(
                name=s["name"],
                amount=s["amount"],
                count=s["count"],
                percentage=round((s["amount"] / c_amt * 100), 1) if c_amt > 0 else 0.0,
            )
            for s in sorted_subs
        ]

        sorted_merchants = sorted(merchant_items_map.values(), key=lambda x: x["amount"], reverse=True)
        merchant_items_list: List[CategorySubItem] = [
            CategorySubItem(
                name=m["name"],
                amount=m["amount"],
                count=m["count"],
                percentage=round((m["amount"] / c_amt * 100), 1) if c_amt > 0 else 0.0,
            )
            for m in sorted_merchants
        ]

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
                sub_items=sub_items_list,
                merchant_items=merchant_items_list,
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
