import pytest
from app.database.schema import init_database
from app.services.transaction_service import (
    create_variable_expense,
    get_variable_expenses,
    update_variable_expense,
    delete_variable_expense,
)
from app.database.connection import get_connection
from app.models.schemas import VariableExpenseCreate, VariableExpenseUpdate
from app.services.analytics_service import get_monthly_summary, get_annual_dashboard
from app.services.spreadsheet_service import export_to_excel_bytes, import_from_excel_file, export_all_json, restore_all_json

@pytest.fixture(autouse=True)
def setup_db():
    init_database()

def get_first_cat_and_pay():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories LIMIT 1")
    cat_id = cur.fetchone()["id"]
    cur.execute("SELECT id FROM payment_methods LIMIT 1")
    pay_id = cur.fetchone()["id"]
    conn.close()
    return cat_id, pay_id

def test_variable_expense_lifecycle():
    cat_id, pay_id = get_first_cat_and_pay()
    # 1. Create
    data = VariableExpenseCreate(
        transaction_date="2026-09-13",
        category_id=cat_id,
        title="스타벅스 카페라떼",
        payment_method_id=pay_id,
        amount=5500,
        memo="테스트 메모"
    )
    expense_id = create_variable_expense(data)
    assert expense_id > 0

    # 2. Read
    items = get_variable_expenses(year=2026, month=9)
    matching = [i for i in items if i.id == expense_id]
    assert len(matching) == 1
    assert matching[0].title == "스타벅스 카페라떼"
    assert matching[0].amount == 5500

    # 3. Update
    up_ok = update_variable_expense(expense_id, VariableExpenseUpdate(amount=6000, title="스타벅스 벤티"))
    assert up_ok is True
    items_after = get_variable_expenses(year=2026, month=9)
    assert [i for i in items_after if i.id == expense_id][0].amount == 6000

    # 4. Delete
    del_ok = delete_variable_expense(expense_id)
    assert del_ok is True

def test_monthly_summary_and_annual_dashboard():
    cat_id, pay_id = get_first_cat_and_pay()
    # Insert a test transaction
    create_variable_expense(VariableExpenseCreate(
        transaction_date="2026-09-13",
        category_id=cat_id,
        title="마트 장보기",
        payment_method_id=pay_id,
        amount=150000
    ))

    summary = get_monthly_summary(2026, 9)
    assert summary.variable_expense >= 150000
    assert summary.total_income >= 0
    assert summary.fixed_expense >= 0
    assert summary.savings_investment >= 0
    assert summary.total_expense == summary.fixed_expense + summary.variable_expense
    assert summary.balance == summary.total_income - summary.total_expense - summary.savings_investment

    annual = get_annual_dashboard(2026)
    assert len(annual.months) == 12
    assert annual.annual_total.month_name == "연간 합계"
    assert annual.monthly_average.month_name == "월평균"

def test_spreadsheet_export_and_import():
    # 1. Export XLSX
    excel_bytes = export_to_excel_bytes(2026)
    assert len(excel_bytes) > 0

    # 2. Import the generated XLSX
    imported = import_from_excel_file(excel_bytes)
    assert imported["fixed_incomes"] > 0
    assert imported["fixed_expenses"] > 0
    assert imported["savings"] > 0

def test_json_backup_and_restore():
    json_data = export_all_json()
    assert "categories" in json_data
    assert "variable_expenses" in json_data
    assert len(json_data["categories"]) > 0

    ok = restore_all_json(json_data)
    assert ok is True
