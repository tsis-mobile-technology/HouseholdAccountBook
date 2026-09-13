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
    payload = {
        "transaction_date": "2026-09-13",
        "category_id": 1,
        "title": "API 테스트 점심",
        "payment_method_id": 1,
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
