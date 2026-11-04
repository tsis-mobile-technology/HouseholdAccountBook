import io
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Dict, List, Tuple, Optional, Any
import openpyxl

from app.database.connection import get_connection, get_db_cursor
from app.models.schemas import CardParsedItem, CardPreviewResponse, CardConfirmItem, CardConfirmResponse

# ---------------------------------------------------------------------------
# Category Keyword Dictionaries (Ordered by priority)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = [
    # High priority specific categories first
    ("별콩이", ["동물병원", "동물", "반려", "펫", "도그", "캣", "멍멍", "야옹"]),
    ("학원/도서", [
        "학원", "교육", "에듀", "학교", "도서", "서점", "교보", "예스24", "알라딘",
        "영풍문고", "등록금", "대학", "고등", "강의", "클래스", "스터디", "독서실"
    ]),
    ("의료/건강", [
        "병원", "의원", "약국", "치과", "이비인후과", "내과", "피부과", "한의원",
        "안과", "정형외과", "메디컬", "보건소", "재활", "소아과", "검진", "비뇨", "산부인과"
    ]),
    ("교통/차량", [
        "철도", "코레일", "srt", "버스", "지하철", "택시", "카카오t", "주유",
        "주유소", "세차", "카센터", "하이패스", "티머니", "교통", "공항", "모빌리티",
        "오토오아시스", "주차", "티맵", "쏘카", "그린카"
    ]),
    ("문화/여가", [
        "cgv", "롯데시네마", "메가박스", "영화", "넷플릭스", "유튜브", "멜론",
        "인터파크", "티켓", "골프", "헬스", "피트니스", "볼링", "당구", "공연",
        "전시", "리조트", "호텔", "펜션", "야놀자", "여기어때", "에어비앤비"
    ]),
    ("외식/카페", [
        "식당", "카페", "커피", "스타벅스", "메가", "컴포즈", "파리바게뜨", "베이커리",
        "빵", "마라", "치킨", "피자", "버거", "김밥", "분식", "주점", "콩두", "식음",
        "루브레드", "다복향", "춘리", "맥도날드", "서브웨이", "갈비", "삼겹살", "우동",
        "돈까스", "초밥", "이자카야", "포차", "호프", "투썸", "이디야", "빽다방",
        "아웃백", "스테이크", "공차", "롯데리아", "버거킹", "배민", "우아한형제들",
        "엔제리너스", "베스킨", "던킨", "설빙", "파리크라상", "할리스", "폴바셋",
        "요기요", "쿠팡이츠", "국밥", "짜장", "짬뽕", "중화요리", "떡볶이"
    ]),
    ("식비", [
        "마트", "이마트", "트레이더스", "코스트코", "홈플러스", "농협", "하나로",
        "반찬", "정육", "과일", "쿠팡", "마켓컬리", "오아시스", "식품", "푸드",
        "축산", "수산", "정육점", "청과", "야채", "로컬푸드"
    ]),
    ("쇼핑/의류", [
        "백화점", "아울렛", "몰", "유니클로", "자라", "무신사", "지그재그", "에이블리",
        "오늘의집", "ssg", "네이버파이낸셜", "패션", "의류", "슈즈", "아이파크",
        "원에프엔씨", "마리앙", "abc마트", "스파오", "탑텐", "에이치엔엠", "나이키", "아디다스"
    ]),
    ("생활용품", [
        "다이소", "올리브영", "편의점", "gs25", "cu", "세븐일레븐", "세탁",
        "크린토피아", "철물", "이케아", "모던하우스", "무인양품", "미니소", "문구", "오피스디포"
    ]),
]

# ---------------------------------------------------------------------------
# HTML Table Parser Helper (for Shinhan & Hyundai Card .xls files)
# ---------------------------------------------------------------------------
class SimpleHTMLTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._curr_table: List[List[str]] = []
        self._curr_row: List[str] = []
        self._curr_cell: List[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._curr_table = []
        elif tag == "tr":
            self._curr_row = []
        elif tag in ("td", "th"):
            self._curr_cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._in_cell = False
            self._curr_row.append("".join(self._curr_cell).strip())
        elif tag == "tr":
            if any(self._curr_row):
                self._curr_table.append(self._curr_row)
        elif tag == "table":
            if self._curr_table:
                self.tables.append(self._curr_table)

    def handle_data(self, data):
        if self._in_cell:
            self._curr_cell.append(data)


# ---------------------------------------------------------------------------
# Individual Card Parsers
# ---------------------------------------------------------------------------
def parse_samsung_card(content: bytes) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Parses Samsung Card Excel file (.xlsx).
    Handles:
      - '일시불' sheet: Row 3 header, Row 4+ data
      - '할부' sheet: Row 3 header, Row 4+ data (installment payments due this month)
      - '결제 취소내역(전월 명세서 발송 이후)' sheet: Refunds (negative amounts)
    """
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    items: List[Dict[str, Any]] = []
    statement_month = None

    # 1. 일시불
    if "일시불" in wb.sheetnames:
        sheet = wb["일시불"]
        for r in range(4, sheet.max_row + 1):
            date_raw = str(sheet.cell(row=r, column=1).value or "").strip()
            if not re.match(r"^\d{8}$", date_raw):
                continue
            date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            merchant = str(sheet.cell(row=r, column=3).value or "").strip()
            if not merchant:
                continue

            # Amount: principal (원금 col 10) + fee (이자/수수료 col 11)
            principal_val = sheet.cell(row=r, column=10).value
            fee_val = sheet.cell(row=r, column=11).value or 0
            if principal_val is None or str(principal_val).strip() == "":
                # Fallback to col 4 (이용금액)
                raw_amt = str(sheet.cell(row=r, column=4).value or "0").replace(",", "").strip()
                amt = int(round(float(raw_amt)))
            else:
                amt = int(round(float(principal_val) + float(fee_val)))

            card_memo = str(sheet.cell(row=r, column=2).value or "").strip()
            items.append({
                "transaction_date": date_str,
                "title": merchant,
                "amount": amt,
                "installment": "일시불",
                "memo": f"삼성카드 {card_memo}".strip(),
            })

    # 2. 할부
    if "할부" in wb.sheetnames:
        sheet = wb["할부"]
        for r in range(4, sheet.max_row + 1):
            date_raw = str(sheet.cell(row=r, column=1).value or "").strip()
            if not re.match(r"^\d{8}$", date_raw):
                continue
            date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            merchant = str(sheet.cell(row=r, column=3).value or "").strip()
            if not merchant:
                continue

            months = str(sheet.cell(row=r, column=8).value or "").strip()
            turn = str(sheet.cell(row=r, column=9).value or "").strip()
            inst_str = f"할부 {turn}/{months}" if (months and turn) else "할부"

            principal_val = float(sheet.cell(row=r, column=10).value or 0)
            fee_val = float(sheet.cell(row=r, column=11).value or 0)
            amt = int(round(principal_val + fee_val))

            card_memo = str(sheet.cell(row=r, column=2).value or "").strip()
            items.append({
                "transaction_date": date_str,
                "title": f"{merchant} [할부 {inst_str}]",
                "amount": amt,
                "installment": inst_str,
                "memo": f"삼성카드 {card_memo} 할부".strip(),
            })

    # 3. 결제 취소내역 (전월 명세서 발송 이후)
    cancel_sheet_name = next((s for s in wb.sheetnames if "취소" in s), None)
    if cancel_sheet_name:
        sheet = wb[cancel_sheet_name]
        for r in range(4, sheet.max_row + 1):
            date_raw = str(sheet.cell(row=r, column=1).value or "").strip()
            if not re.match(r"^\d{8}$", date_raw):
                continue
            date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            merchant = str(sheet.cell(row=r, column=3).value or "").strip()
            if not merchant:
                continue

            # 취소금액 at col 5
            cancel_amt_raw = str(sheet.cell(row=r, column=5).value or "0").replace(",", "").strip()
            try:
                cancel_amt = int(round(float(cancel_amt_raw)))
            except ValueError:
                cancel_amt = 0

            # Ensure negative value for refund
            if cancel_amt > 0:
                cancel_amt = -cancel_amt

            card_memo = str(sheet.cell(row=r, column=2).value or "").strip()
            items.append({
                "transaction_date": date_str,
                "title": f"[취소] {merchant}",
                "amount": cancel_amt,
                "installment": "결제취소",
                "memo": f"삼성카드 {card_memo} 결제취소".strip(),
            })

    # Determine statement month from transactions (most frequent YYYY-MM)
    if items:
        month_counts: Dict[str, int] = {}
        for it in items:
            ym = it["transaction_date"][:7]
            month_counts[ym] = month_counts.get(ym, 0) + 1
        statement_month = max(month_counts.items(), key=lambda x: x[1])[0]

    return statement_month, items


def parse_shinhan_card(content: bytes) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Parses Shinhan Card HTML table statement file (.xls).
    """
    html_text = ""
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            html_text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    parser = SimpleHTMLTableParser()
    parser.feed(html_text)

    items: List[Dict[str, Any]] = []
    statement_month = None

    # Detect caption like '2026년11월 이용대금명세서'
    m_cap = re.search(r"(\d{4})년\s*(\d{1,2})월\s*이용대금명세서", html_text)
    if m_cap:
        statement_month = f"{int(m_cap.group(1)):04d}-{int(m_cap.group(2)):02d}"

    # Search for table containing transaction headers
    for tbl in parser.tables:
        if len(tbl) < 2:
            continue
        header_row = tbl[0]
        if any("이용가맹점" in c for c in header_row) and any("이번달 납부금액" in c or "이번달납부금액" in c for c in header_row):
            for r in tbl[1:]:
                if len(r) < 7:
                    continue
                date_col = r[0].strip()
                # Match YYYY.MM.DD
                if not re.match(r"^\d{4}\.\d{2}\.\d{2}$", date_col):
                    continue
                date_str = date_col.replace(".", "-")

                card_info = r[1].strip()
                merchant = r[2].strip()
                if not merchant:
                    continue

                used_amt_str = r[3].replace(",", "").strip()
                try:
                    used_amt = int(used_amt_str)
                except ValueError:
                    used_amt = 0

                installment_period = r[4].strip() if len(r) > 4 else ""
                installment_turn = r[5].strip() if len(r) > 5 else ""

                # 이번달 납부금액: 원금 + 수수료(이자)
                billed_principal_str = r[6].replace(",", "").strip() if len(r) > 6 and r[6] else str(used_amt)
                billed_fee_str = r[7].replace(",", "").strip() if len(r) > 7 and r[7] else "0"

                try:
                    principal = int(billed_principal_str)
                except ValueError:
                    principal = used_amt

                try:
                    fee = int(billed_fee_str)
                except ValueError:
                    fee = 0

                tot_amt = principal + fee

                installment_info = "일시불"
                title = merchant
                if installment_period and installment_turn:
                    installment_info = f"할부 {installment_turn}/{installment_period}"
                    title = f"{merchant} [{installment_info}]"

                items.append({
                    "transaction_date": date_str,
                    "title": title,
                    "amount": tot_amt,
                    "installment": installment_info,
                    "memo": f"신한카드 {card_info}".strip(),
                })
            # Only process the first transactions table
            if items:
                break

    if not statement_month and items:
        month_counts: Dict[str, int] = {}
        for it in items:
            ym = it["transaction_date"][:7]
            month_counts[ym] = month_counts.get(ym, 0) + 1
        statement_month = max(month_counts.items(), key=lambda x: x[1])[0]

    return statement_month, items


def parse_hyundaicard(content: bytes) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Parses Hyundai Card HTML table statement file (.xls).
    """
    html_text = ""
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            html_text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    parser = SimpleHTMLTableParser()
    parser.feed(html_text)

    items: List[Dict[str, Any]] = []
    statement_month = None

    # Detect title like '2026년 11월 이용대금명세서'
    m_cap = re.search(r"(\d{4})년\s*(\d{1,2})월\s*이용대금명세서", html_text)
    if m_cap:
        statement_month = f"{int(m_cap.group(1)):04d}-{int(m_cap.group(2)):02d}"

    for tbl in parser.tables:
        for r in tbl:
            if len(r) < 8:
                continue
            date_col = r[0].strip()

            # Skip summary rows
            if any(k in "".join(r) for k in ("소계", "총 합계", "결제 상세내역", "이용대금명세서")):
                continue
            if date_col == "-" or not date_col:
                continue

            m_date = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_col)
            if not m_date:
                continue
            date_str = f"{int(m_date.group(1)):04d}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"

            card_info = r[1].strip() if len(r) > 1 else ""
            merchant = r[2].strip() if len(r) > 2 else ""
            if not merchant:
                continue

            used_amt_str = r[3].replace(",", "").strip() if len(r) > 3 else "0"
            try:
                used_amt = int(used_amt_str)
            except ValueError:
                used_amt = 0

            inst_col = r[4].strip() if len(r) > 4 else ""

            # 결제원금 (col 7) + 수수료(이자) (col 9)
            principal_str = r[7].replace(",", "").strip() if len(r) > 7 and r[7] else str(used_amt)
            fee_str = r[9].replace(",", "").strip() if len(r) > 9 and r[9] else "0"

            try:
                principal = int(principal_str)
            except ValueError:
                principal = used_amt

            try:
                fee = int(fee_str)
            except ValueError:
                fee = 0

            tot_amt = principal + fee

            installment_info = inst_col if inst_col else "일시불"
            title = merchant
            if inst_col and inst_col != "일시불":
                title = f"{merchant} [할부 {inst_col}]"

            items.append({
                "transaction_date": date_str,
                "title": title,
                "amount": tot_amt,
                "installment": installment_info,
                "memo": f"현대카드 {card_info}".strip(),
            })

    if not statement_month and items:
        month_counts: Dict[str, int] = {}
        for it in items:
            ym = it["transaction_date"][:7]
            month_counts[ym] = month_counts.get(ym, 0) + 1
        statement_month = max(month_counts.items(), key=lambda x: x[1])[0]

    return statement_month, items


# ---------------------------------------------------------------------------
# Auto Detector
# ---------------------------------------------------------------------------
def auto_detect_and_parse(content: bytes, filename: str) -> Tuple[str, str, Optional[str], List[Dict[str, Any]]]:
    """
    Detects card issuer by examining file bytes and filename.
    Returns:
      (issuer_key, issuer_name, statement_month, items)
    """
    fn_lower = filename.lower()

    # 1. Check if binary OpenXML (.xlsx)
    if content.startswith(b"PK\x03\x04"):
        # Most likely Samsung card
        month, items = parse_samsung_card(content)
        return "samsung", "삼성카드", month, items

    # 2. Check HTML contents
    text_preview = content[:2000].decode("utf-8", errors="ignore").lower()

    if "hyundai" in fn_lower or "현대" in text_preview or "zero mobile" in text_preview:
        month, items = parse_hyundaicard(content)
        return "hyundai", "현대카드", month, items

    if "shinhan" in fn_lower or "신한" in text_preview or "신용카드" in text_preview:
        month, items = parse_shinhan_card(content)
        return "shinhan", "신한카드", month, items

    # Fallback checks based on filename
    if "samsung" in fn_lower or "삼성" in fn_lower:
        month, items = parse_samsung_card(content)
        return "samsung", "삼성카드", month, items

    # Try Shinhan then Hyundai
    try:
        month, items = parse_shinhan_card(content)
        if items:
            return "shinhan", "신한카드", month, items
    except Exception:
        pass

    try:
        month, items = parse_hyundaicard(content)
        if items:
            return "hyundai", "현대카드", month, items
    except Exception:
        pass

    raise ValueError("지원하지 않는 카드사 명세서 서식이거나 파일 형식을 인식할 수 없습니다.")


# ---------------------------------------------------------------------------
# Category & Deduplication Enrichment
# ---------------------------------------------------------------------------
def get_categories_lookup() -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """Loads active categories from DB."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, color_hex, icon, sort_order FROM categories WHERE is_active = 1 ORDER BY sort_order ASC")
        rows = [dict(r) for r in cur.fetchall()]
        cat_map = {r["name"]: r["id"] for r in rows}
        return cat_map, rows
    finally:
        conn.close()


def get_payment_method_id_by_name(name: str) -> int:
    """Finds payment method ID or creates it if missing."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM payment_methods WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        # Fallback to '신용카드'
        cur.execute("SELECT id FROM payment_methods WHERE name = '신용카드'")
        fallback = cur.fetchone()
        return fallback["id"] if fallback else 1
    finally:
        conn.close()


def classify_category(title: str, cat_map: Dict[str, int], cat_list: List[Dict[str, Any]]) -> Tuple[int, str]:
    """Auto-classifies merchant into a category."""
    t = title.lower()
    for cat_name, keywords in CATEGORY_KEYWORDS:
        if cat_name in cat_map:
            for kw in keywords:
                if kw.lower() in t:
                    return cat_map[cat_name], cat_name

    # Default to '기타' if present, or first category
    if "기타" in cat_map:
        return cat_map["기타"], "기타"
    if cat_list:
        return cat_list[0]["id"], cat_list[0]["name"]
    return 1, "식비"


def enrich_and_detect_duplicates(
    raw_items: List[Dict[str, Any]],
    issuer_name: str,
    payment_method_id: int
) -> List[CardParsedItem]:
    """
    Enriches parsed card items with category classification and duplicate checks.
    """
    cat_map, cat_list = get_categories_lookup()

    if not raw_items:
        return []

    # Get date boundaries
    dates = [it["transaction_date"] for it in raw_items if it.get("transaction_date")]
    if not dates:
        min_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        max_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        min_d = min(dates)
        max_d = max(dates)
        # Add 3 days buffer on both sides for matching
        min_date = (datetime.strptime(min_d, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")
        max_date = (datetime.strptime(max_d, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")

    # Fetch existing transactions in buffer range
    conn = get_connection()
    existing_list = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, transaction_date, title, amount, category_id, payment_method_id
            FROM variable_expenses
            WHERE transaction_date >= ? AND transaction_date <= ?
        """, (min_date, max_date))
        existing_list = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    result: List[CardParsedItem] = []
    used_existing_ids = set()

    for idx, item in enumerate(raw_items):
        t_date = item["transaction_date"]
        raw_title = item["title"]
        amt = item["amount"]
        inst = item.get("installment", "")
        memo = item.get("memo", "")

        cat_id, cat_name = classify_category(raw_title, cat_map, cat_list)

        # Duplicate checking:
        # 1. Exact match: same date AND same amount
        # 2. Near-date match: within ±1 day AND same amount AND similar title
        is_dup = False
        dup_reason = ""
        matched_id = None

        clean_merchant = re.sub(r"\[할부.*?\]|\[취소.*?\]|\(주\)|주식회사|유한회사|\s+", "", raw_title).lower()

        for ex in existing_list:
            if ex["id"] in used_existing_ids:
                continue

            ex_date = ex["transaction_date"]
            ex_amt = ex["amount"]
            ex_title = ex["title"]
            clean_ex_title = re.sub(r"\[할부.*?\]|\[취소.*?\]|\(주\)|주식회사|유한회사|\s+", "", ex_title).lower()

            # Exact date & exact amount
            if ex_date == t_date and ex_amt == amt:
                is_dup = True
                matched_id = ex["id"]
                used_existing_ids.add(ex["id"])
                dup_reason = f"기존 내역({ex_date} '{ex_title}', {ex_amt:,}원)과 일자·금액 일치"
                break

            # Near date (±1 day) & exact amount & title overlap
            d1 = datetime.strptime(t_date, "%Y-%m-%d")
            d2 = datetime.strptime(ex_date, "%Y-%m-%d")
            if abs((d1 - d2).days) <= 1 and ex_amt == amt:
                if (clean_merchant and clean_merchant in clean_ex_title) or (clean_ex_title and clean_ex_title in clean_merchant):
                    is_dup = True
                    matched_id = ex["id"]
                    used_existing_ids.add(ex["id"])
                    dup_reason = f"기존 내역({ex_date} '{ex_title}', {ex_amt:,}원)과 유사 가맹점·금액 일치"
                    break

        default_action = "skip" if is_dup else "add_new"

        result.append(CardParsedItem(
            temp_id=f"card_{idx}",
            transaction_date=t_date,
            title=raw_title,
            amount=amt,
            category_id=cat_id,
            category_name=cat_name,
            payment_method_id=payment_method_id,
            payment_method_name=issuer_name,
            installment=inst,
            memo=memo,
            is_duplicate=is_dup,
            duplicate_reason=dup_reason,
            existing_expense_id=matched_id,
            action=default_action,
        ))

    return result


# ---------------------------------------------------------------------------
# Confirmation & Import Execution
# ---------------------------------------------------------------------------
def execute_card_import(items: List[CardConfirmItem]) -> CardConfirmResponse:
    """
    Executes transaction import based on user choices:
      - 'add_new': Inserts new variable_expense
      - 'merge': Updates existing variable_expense
      - 'skip': No DB action
    """
    added = 0
    merged = 0
    skipped = 0

    with get_db_cursor() as cur:
        for item in items:
            if item.action == "skip":
                skipped += 1
                continue

            elif item.action == "merge" and item.existing_expense_id:
                # Merge: Update existing record with card details
                cur.execute("""
                    UPDATE variable_expenses
                    SET title = ?,
                        category_id = ?,
                        payment_method_id = ?,
                        amount = ?,
                        memo = CASE 
                            WHEN memo IS NULL OR memo = '' THEN ? 
                            ELSE memo || ' | ' || ? 
                        END,
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (
                    item.title,
                    item.category_id,
                    item.payment_method_id,
                    item.amount,
                    item.memo or "",
                    item.memo or "",
                    item.existing_expense_id
                ))
                merged += 1

            elif item.action in ("add_new", "merge"):
                # Insert as new transaction
                cur.execute("""
                    INSERT INTO variable_expenses (transaction_date, category_id, title, payment_method_id, amount, memo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item.transaction_date,
                    item.category_id,
                    item.title,
                    item.payment_method_id,
                    item.amount,
                    item.memo or ""
                ))
                added += 1

    total = added + merged + skipped
    return CardConfirmResponse(
        status="success",
        added=added,
        merged=merged,
        skipped=skipped,
        total=total,
        message=f"카드 내역 처리 완료: 신규 추가 {added}건, 병합/수정 {merged}건, 건너뜀 {skipped}건 (총 {total}건)"
    )
