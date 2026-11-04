import io
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.card_statement_service import (
    parse_samsung_card,
    parse_shinhan_card,
    parse_hyundaicard,
    auto_detect_and_parse,
    enrich_and_detect_duplicates,
    execute_card_import,
)
from app.models.schemas import CardConfirmItem
from app.database.connection import get_db_cursor

client = TestClient(app)

TEMPLATES_DIR = Path("templates")

def test_parse_samsung_card_template():
    p = TEMPLATES_DIR / "samsungcard_20261110.xlsx"
    assert p.exists()
    content = p.read_bytes()
    month, items = parse_samsung_card(content)
    assert month == "2026-10" or month == "2026-09"
    assert len(items) == 126
    total_amt = sum(x["amount"] for x in items)
    # Reconciles exactly with the statement total: 8,397,217 won
    assert total_amt == 8397217

    # Check installment item
    installments = [x for x in items if "할부" in x["installment"]]
    assert len(installments) > 0
    # Check refund item
    refunds = [x for x in items if x["amount"] < 0]
    assert len(refunds) == 1
    assert refunds[0]["amount"] == -66200

def test_parse_shinhan_card_template():
    p = TEMPLATES_DIR / "2026년11월 이용대금명세서(신용카드).xls"
    assert p.exists()
    content = p.read_bytes()
    month, items = parse_shinhan_card(content)
    assert month == "2026-11"
    assert len(items) == 17
    total_amt = sum(x["amount"] for x in items)
    # Reconciles exactly with the statement billed total: 495,130 won
    assert total_amt == 495130

def test_parse_hyundai_card_template():
    p = TEMPLATES_DIR / "hyundaicard_20261105.xls"
    assert p.exists()
    content = p.read_bytes()
    month, items = parse_hyundaicard(content)
    assert month == "2026-11"
    assert len(items) == 10
    total_amt = sum(x["amount"] for x in items)
    # Reconciles exactly with the statement billed total: 1,026,910 won
    assert total_amt == 1026910

def test_auto_detect_and_parse():
    # Samsung
    s_bytes = (TEMPLATES_DIR / "samsungcard_20261110.xlsx").read_bytes()
    k1, name1, m1, it1 = auto_detect_and_parse(s_bytes, "samsungcard_20261110.xlsx")
    assert k1 == "samsung"
    assert name1 == "삼성카드"
    assert len(it1) == 126

    # Shinhan
    sh_bytes = (TEMPLATES_DIR / "2026년11월 이용대금명세서(신용카드).xls").read_bytes()
    k2, name2, m2, it2 = auto_detect_and_parse(sh_bytes, "2026년11월 이용대금명세서(신용카드).xls")
    assert k2 == "shinhan"
    assert name2 == "신한카드"
    assert len(it2) == 17

    # Hyundai
    hy_bytes = (TEMPLATES_DIR / "hyundaicard_20261105.xls").read_bytes()
    k3, name3, m3, it3 = auto_detect_and_parse(hy_bytes, "hyundaicard_20261105.xls")
    assert k3 == "hyundai"
    assert name3 == "현대카드"
    assert len(it3) == 10

def test_card_preview_and_duplicate_detection():
    # Insert a manual transaction that should collide with Hyundai card
    # In Hyundai: 2026-10-05 코스트코코리아 251,850원
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO variable_expenses (transaction_date, category_id, title, payment_method_id, amount, memo)
            VALUES ('2026-10-05', 1, '코스트코 장보기 수기등록', 1, 251850, '직접 입력한 메모')
        """)
        manual_id = cur.lastrowid

    hy_bytes = (TEMPLATES_DIR / "hyundaicard_20261105.xls").read_bytes()
    response = client.post(
        "/api/cards/preview",
        files={"file": ("hyundaicard_20261105.xls", io.BytesIO(hy_bytes), "application/vnd.ms-excel")},
        data={"target_year": 2026, "target_month": 11}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issuer"] == "hyundai"
    assert data["total_count"] == 10
    assert data["duplicate_count"] >= 1

    dup_items = [it for it in data["items"] if it["is_duplicate"]]
    assert len(dup_items) >= 1
    target_dup = next(it for it in dup_items if it["amount"] == 251850)
    assert target_dup["action"] == "skip"
    assert target_dup["existing_expense_id"] == manual_id

    # Clean up test manual item
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM variable_expenses WHERE id = ?", (manual_id,))

def test_card_confirm_actions():
    # Test execute_card_import with add_new, merge, skip
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO variable_expenses (transaction_date, category_id, title, payment_method_id, amount, memo)
            VALUES ('2026-10-08', 6, '남시약국 기존', 1, 25000, '기존메모')
        """)
        existing_id = cur.lastrowid

    items_to_confirm = [
        CardConfirmItem(
            action="merge",
            transaction_date="2026-10-08",
            category_id=6,
            payment_method_id=8, # 현대카드
            title="남시약국 (카드병합)",
            amount=25000,
            memo="현대카드 승인",
            existing_expense_id=existing_id,
        ),
        CardConfirmItem(
            action="skip",
            transaction_date="2026-10-21",
            category_id=1,
            payment_method_id=8,
            title="코스트코 건너뛰기",
            amount=15100,
        ),
        CardConfirmItem(
            action="add_new",
            transaction_date="2026-10-21",
            category_id=1,
            payment_method_id=8,
            title="코스트코 신규추가",
            amount=166700,
            memo="신규 추가 건",
        )
    ]

    res = execute_card_import(items_to_confirm)
    assert res.added == 1
    assert res.merged == 1
    assert res.skipped == 1

    # Verify DB state
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM variable_expenses WHERE id = ?", (existing_id,))
        merged_row = cur.fetchone()
        assert merged_row["title"] == "남시약국 (카드병합)"
        assert "현대카드 승인" in merged_row["memo"]

        cur.execute("SELECT * FROM variable_expenses WHERE title = '코스트코 신규추가'")
        new_row = cur.fetchone()
        assert new_row is not None
        assert new_row["amount"] == 166700

        # Clean up
        cur.execute("DELETE FROM variable_expenses WHERE id = ?", (existing_id,))
        cur.execute("DELETE FROM variable_expenses WHERE title = '코스트코 신규추가'")

def test_spending_patterns_api():
    # Insert test dataset for 2026-10
    test_rows = [
        ("2026-10-02", 1, "이마트 장보기", 1, 100000),     # 식비, Fri (weekday)
        ("2026-10-03", 2, "스타벅스 커피", 1, 20000),      # 외식, Sat (weekend)
        ("2026-10-04", 2, "아웃백 디너", 8, 150000),       # 외식, Sun (weekend, 현대카드)
        ("2026-10-15", 3, "주유소", 6, 80000),             # 교통, Thu (weekday, 삼성카드)
        ("2026-10-20", 6, "병원 진료", 7, 50000),          # 의료, Tue (weekday, 신한카드)
    ]
    with get_db_cursor() as cur:
        for d, c, t, p, a in test_rows:
            cur.execute("""
                INSERT INTO variable_expenses (transaction_date, category_id, title, payment_method_id, amount)
                VALUES (?, ?, ?, ?, ?)
            """, (d, c, t, p, a))

    res = client.get("/api/analytics/spending-patterns?year=2026&month=10")
    assert res.status_code == 200
    data = res.json()
    assert data["year"] == 2026
    assert data["month"] == 10
    assert data["total_spending"] == 400000
    assert data["transaction_count"] == 5
    assert data["daily_average"] > 0
    assert len(data["categories"]) > 0
    assert len(data["payment_methods"]) > 0
    assert len(data["weekly"]) == 5
    assert len(data["day_of_week"]) == 7
    assert len(data["top_merchants"]) > 0
    assert data["weekday_spending"] > 0
    assert data["weekend_spending"] > 0

    # Path param version
    res2 = client.get("/api/analytics/spending-patterns/2026/10")
    assert res2.status_code == 200
    assert res2.json()["total_spending"] == 400000

    # Clean up test rows
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM variable_expenses WHERE transaction_date LIKE '2026-10%'")

def test_frontend_assets_served():
    # 1. Verify index.html contains necessary UI elements
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert 'id="view-spending"' in html
    assert 'id="modalCardUpload"' in html
    assert 'id="chartCategoryDonut"' in html
    assert 'id="chartPaymentMethodPie"' in html
    assert 'id="chartWeeklyBar"' in html
    assert 'id="chartDayOfWeekBar"' in html
    assert 'openCardUploadModal()' in html

    # 2. Verify app.js is served and contains new logic
    res_js = client.get("/static/js/app.js")
    assert res_js.status_code == 200
    js = res_js.text
    assert "loadSpendingPatterns" in js
    assert "openCardUploadModal" in js
    assert "analyzeCardFile" in js
    assert "confirmCardImport" in js
    assert "renderSpendingCategoryChart" in js

def test_e2e_card_upload_and_spending_analysis():
    # Full flow:
    # 1. Upload Hyundai Card file via preview API
    hy_bytes = (TEMPLATES_DIR / "hyundaicard_20261105.xls").read_bytes()
    res = client.post(
        "/api/cards/preview",
        files={"file": ("hyundaicard_20261105.xls", io.BytesIO(hy_bytes), "application/vnd.ms-excel")},
        data={"target_year": 2026, "target_month": 11}
    )
    assert res.status_code == 200
    preview_data = res.json()
    assert preview_data["total_count"] == 10
    assert preview_data["total_amount"] == 1026910

    # 2. Confirm import all items as add_new
    confirm_payload = {
        "items": [
            {
                "action": it["action"],
                "transaction_date": it["transaction_date"],
                "category_id": it["category_id"],
                "payment_method_id": it["payment_method_id"],
                "title": it["title"],
                "amount": it["amount"],
                "memo": it["memo"]
            }
            for it in preview_data["items"]
        ]
    }
    confirm_res = client.post("/api/cards/confirm", json=confirm_payload)
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["added"] == 10

    # 3. Query spending pattern analytics for month 10 (since Hyundai card October transactions sum to 527,710)
    analytics_res = client.get("/api/analytics/spending-patterns?year=2026&month=10")
    assert analytics_res.status_code == 200
    adata = analytics_res.json()
    assert adata["total_spending"] == 527710
    assert adata["transaction_count"] == 5
    assert len(adata["top_merchants"]) >= 1
    # Check top merchant in Hyundai: 코스트코 or 쿠팡 or 남시약국
    assert any("코스트코" in m["merchant"] or "남시약국" in m["merchant"] for m in adata["top_merchants"])

    # 4. Re-upload same file to verify duplicate detection works
    res_dup = client.post(
        "/api/cards/preview",
        files={"file": ("hyundaicard_20261105.xls", io.BytesIO(hy_bytes), "application/vnd.ms-excel")},
        data={"target_year": 2026, "target_month": 11}
    )
    assert res_dup.status_code == 200
    dup_preview = res_dup.json()
    # All 10 items should now be flagged as duplicate
    assert dup_preview["duplicate_count"] == 10
    assert all(it["is_duplicate"] for it in dup_preview["items"])

    # 5. Clean up imported rows
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM variable_expenses WHERE transaction_date LIKE '2026-10%' OR transaction_date LIKE '2026-09%' OR transaction_date LIKE '2026-08%'")

def test_samsung_and_shinhan_preview_api():
    # 1. Samsung card preview
    s_bytes = (TEMPLATES_DIR / "samsungcard_20261110.xlsx").read_bytes()
    res_s = client.post(
        "/api/cards/preview",
        files={"file": ("samsungcard_20261110.xlsx", io.BytesIO(s_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert res_s.status_code == 200
    s_data = res_s.json()
    assert s_data["issuer"] == "samsung"
    assert s_data["total_count"] == 126
    assert s_data["total_amount"] == 8397217

    # 2. Shinhan card preview
    sh_bytes = (TEMPLATES_DIR / "2026년11월 이용대금명세서(신용카드).xls").read_bytes()
    res_sh = client.post(
        "/api/cards/preview",
        files={"file": ("2026년11월 이용대금명세서(신용카드).xls", io.BytesIO(sh_bytes), "application/vnd.ms-excel")}
    )
    assert res_sh.status_code == 200
    sh_data = res_sh.json()
    assert sh_data["issuer"] == "shinhan"
    assert sh_data["total_count"] == 17
    assert sh_data["total_amount"] == 495130


