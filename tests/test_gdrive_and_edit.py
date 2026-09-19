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

def test_modify_transaction_api():
    # 1. Create a transaction
    post_res = client.post("/api/transactions", json={
        "transaction_date": "2026-09-19",
        "category_id": 1,
        "title": "테스트 수정 전 커피",
        "payment_method_id": 1,
        "amount": 4500,
        "memo": "아메리카노"
    })
    assert post_res.status_code == 200
    tx_id = post_res.json()["id"]

    # 2. Modify it
    put_res = client.put(f"/api/transactions/{tx_id}", json={
        "title": "테스트 수정 후 라떼",
        "amount": 5000,
        "memo": "바닐라라떼"
    })
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "success"

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
