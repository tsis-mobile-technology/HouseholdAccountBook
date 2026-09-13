from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "스마트 가계부" in response.text

def test_meta_endpoints():
    r1 = client.get("/api/meta/categories")
    assert r1.status_code == 200
    assert len(r1.json()) >= 6

    r2 = client.get("/api/meta/payment-methods")
    assert r2.status_code == 200
    assert len(r2.json()) >= 4

    r3 = client.get("/api/meta/network-info")
    assert r3.status_code == 200
    data = r3.json()
    assert "local_ip" in data
    assert "mobile_url" in data
    assert "qr_code" in data
    assert data["qr_code"].startswith("data:image/png;base64,")

def test_transaction_api_and_overview():
    cat_id = client.get("/api/meta/categories").json()[0]["id"]
    pay_id = client.get("/api/meta/payment-methods").json()[0]["id"]
    payload = {
        "transaction_date": "2026-09-13",
        "category_id": cat_id,
        "title": "API 테스트 점심",
        "payment_method_id": pay_id,
        "amount": 9000,
        "memo": "김치찌개"
    }
    r = client.post("/api/transactions", json=payload)
    assert r.status_code == 200
    res_data = r.json()
    assert res_data["status"] == "success"
    item_id = res_data["id"]

    # Overview
    r_ov = client.get("/api/transactions/overview")
    assert r_ov.status_code == 200
    ov_data = r_ov.json()
    assert ov_data["today_expense_total"] >= 9000
    assert ov_data["today_transaction_count"] >= 1

    # Cleanup
    client.delete(f"/api/transactions/{item_id}")

def test_analytics_and_export_api():
    r_mon = client.get("/api/analytics/monthly/2026/9")
    assert r_mon.status_code == 200
    assert r_mon.json()["month"] == 9

    r_ann = client.get("/api/analytics/annual/2026")
    assert r_ann.status_code == 200
    assert len(r_ann.json()["months"]) == 12

    r_exp = client.get("/api/spreadsheet/export/2026")
    assert r_exp.status_code == 200
    assert r_exp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    r_bak = client.get("/api/spreadsheet/backup-json")
    assert r_bak.status_code == 200
    assert "categories" in r_bak.json()

def test_reset_api_with_confirmation():
    # 1. Invalid confirmation fails
    r_bad = client.post("/api/spreadsheet/reset", json={"confirm_text": "잘못된입력"})
    assert r_bad.status_code == 400

    cat_id = client.get("/api/meta/categories").json()[0]["id"]
    pay_id = client.get("/api/meta/payment-methods").json()[0]["id"]

    # 2. Add an item before reset
    client.post("/api/transactions", json={
        "transaction_date": "2026-09-13",
        "category_id": cat_id,
        "title": "초기화 전 테스트 항목",
        "payment_method_id": pay_id,
        "amount": 7777,
        "memo": "삭제될 항목"
    })
    r_check = client.get("/api/transactions?year=2026&month=9")
    assert any(i["title"] == "초기화 전 테스트 항목" for i in r_check.json())

    # 3. Valid confirmation succeeds
    r_ok = client.post("/api/spreadsheet/reset", json={"confirm_text": "초기화"})
    assert r_ok.status_code == 200
    assert r_ok.json()["status"] == "success"
    assert "backup_file" in r_ok.json()

    # 4. Verify transactions are cleared
    r_after = client.get("/api/transactions?year=2026&month=9")
    assert len(r_after.json()) == 0

    # 5. Verify default categories are still intact
    r_cats = client.get("/api/meta/categories")
    assert len(r_cats.json()) >= 6

