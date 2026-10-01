import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_gdrive_status():
    response = client.get("/api/gdrive/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "connected" in data
    assert "schedule" in data
    assert "local_backup_count" in data

def test_gdrive_schedule_update():
    # Valid schedule
    response = client.post("/api/gdrive/schedule", json={"schedule": "daily"})
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"] == "daily"

    # Reset back to off
    response = client.post("/api/gdrive/schedule", json={"schedule": "off"})
    assert response.status_code == 200

    # Invalid schedule
    response = client.post("/api/gdrive/schedule", json={"schedule": "invalid_val"})
    assert response.status_code == 400

def test_gdrive_local_backups():
    response = client.get("/api/gdrive/local-backups")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["backups"], list)

def test_gdrive_folder_id():
    response = client.post("/api/gdrive/folder-id", json={"folder_id": "test_folder_12345"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["folder_id"] == "test_folder_12345"

    # Reset
    res_reset = client.post("/api/gdrive/folder-id", json={"folder_id": None})
    assert res_reset.status_code == 200
    assert res_reset.json()["folder_id"] is None

def test_gdrive_oauth_client_config():
    response = client.post("/api/gdrive/oauth/client-secrets", json={
        "client_id": "test-client-id.apps.googleusercontent.com",
        "client_secret": "test-client-secret"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Test OAuth URL generation with registered client
    url_res = client.get("/api/gdrive/oauth/url?redirect_uri=http://localhost:8000/api/gdrive/oauth/callback")
    assert url_res.status_code == 200
    data = url_res.json()
    assert data["status"] == "success"
    assert "https://accounts.google.com/o/oauth2/auth" in data["url"]

def test_modify_transaction_api():
    # 1. Create a transaction with 10-won unit (e.g., 4,570 KRW)
    post_res = client.post("/api/transactions", json={
        "transaction_date": "2026-09-19",
        "category_id": 1,
        "title": "테스트 수정 전 커피",
        "payment_method_id": 1,
        "amount": 4570,
        "memo": "아메리카노"
    })
    assert post_res.status_code == 200
    tx_id = post_res.json()["id"]

    # Verify amount saved correctly
    get_res = client.get("/api/transactions?year=2026&month=9")
    assert get_res.status_code == 200
    item = next(it for it in get_res.json() if it["id"] == tx_id)
    assert item["amount"] == 4570

    # 2. Modify it with 1-won unit (e.g., 5,234 KRW)
    put_res = client.put(f"/api/transactions/{tx_id}", json={
        "title": "테스트 수정 후 라떼",
        "amount": 5234,
        "memo": "바닐라라떼"
    })
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "success"

    # Verify updated amount
    get_res2 = client.get("/api/transactions?year=2026&month=9")
    item2 = next(it for it in get_res2.json() if it["id"] == tx_id)
    assert item2["amount"] == 5234

    # 3. Clean up
    del_res = client.delete(f"/api/transactions/{tx_id}")
    assert del_res.status_code == 200

def test_save_fixed_plans_put_and_post():
    payload = {
        "year": 2026,
        "month": 9,
        "incomes": [
            {"item_name": "월급", "day": "25", "description": "기본급", "amount": 3500000}
        ],
        "expenses": [
            {"item_name": "관리비", "day": "15", "description": "아파트", "amount": 200000}
        ],
        "savings": [
            {"item_name": "청약", "day": "10", "description": "주택청약", "amount": 100000}
        ],
        "is_template": False
    }

    # Test PUT
    put_res = client.put("/api/fixed-plans/2026/9", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "success"

    # Test GET
    get_res = client.get("/api/fixed-plans/2026/9")
    assert get_res.status_code == 200
    plans = get_res.json()
    assert len(plans["incomes"]) == 1
    assert plans["incomes"][0]["item_name"] == "월급"
    assert plans["incomes"][0]["amount"] == 3500000

    # Test payload without year and month (as sent from frontend extractRows)
    payload_without_ym = {
        "incomes": [
            {"item_name": "월급(인상)", "day": "25", "description": "기본급", "amount": 3800000}
        ],
        "expenses": [],
        "savings": []
    }
    put_res2 = client.put("/api/fixed-plans/2026/9", json=payload_without_ym)
    assert put_res2.status_code == 200

    get_res2 = client.get("/api/fixed-plans/2026/9")
    assert get_res2.status_code == 200
    assert get_res2.json()["incomes"][0]["item_name"] == "월급(인상)"
