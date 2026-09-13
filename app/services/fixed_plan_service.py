from typing import Dict, List
from app.database.connection import get_connection, get_db_cursor
from app.models.schemas import FixedPlanItem

def get_month_fixed_plans(year: int, month: int) -> Dict[str, List[FixedPlanItem]]:
    conn = get_connection()
    try:
        cur = conn.cursor()

        # 1. Incomes
        cur.execute("""
            SELECT id, year, month, item_name, expected_day as day, description, amount, is_template
            FROM fixed_incomes
            WHERE year = ? AND month = ?
            ORDER BY id ASC
        """, (year, month))
        incomes = [FixedPlanItem(**dict(r)) for r in cur.fetchall()]
        if not incomes:
            # Fallback to templates
            cur.execute("""
                SELECT id, year, month, item_name, expected_day as day, description, amount, is_template
                FROM fixed_incomes
                WHERE is_template = 1
                ORDER BY id ASC
            """)
            incomes = [FixedPlanItem(
                id=None,
                year=year,
                month=month,
                item_name=r["item_name"],
                day=r["day"],
                description=r["description"],
                amount=r["amount"],
                is_template=0
            ) for r in cur.fetchall()]

        # 2. Expenses
        cur.execute("""
            SELECT id, year, month, item_name, withdrawal_day as day, description, amount, is_template
            FROM fixed_expenses
            WHERE year = ? AND month = ?
            ORDER BY id ASC
        """, (year, month))
        expenses = [FixedPlanItem(**dict(r)) for r in cur.fetchall()]
        if not expenses:
            cur.execute("""
                SELECT id, year, month, item_name, withdrawal_day as day, description, amount, is_template
                FROM fixed_expenses
                WHERE is_template = 1
                ORDER BY id ASC
            """)
            expenses = [FixedPlanItem(
                id=None,
                year=year,
                month=month,
                item_name=r["item_name"],
                day=r["day"],
                description=r["description"],
                amount=r["amount"],
                is_template=0
            ) for r in cur.fetchall()]

        # 3. Savings
        cur.execute("""
            SELECT id, year, month, item_name, payment_day as day, description, amount, is_template
            FROM savings_investments
            WHERE year = ? AND month = ?
            ORDER BY id ASC
        """, (year, month))
        savings = [FixedPlanItem(**dict(r)) for r in cur.fetchall()]
        if not savings:
            cur.execute("""
                SELECT id, year, month, item_name, payment_day as day, description, amount, is_template
                FROM savings_investments
                WHERE is_template = 1
                ORDER BY id ASC
            """)
            savings = [FixedPlanItem(
                id=None,
                year=year,
                month=month,
                item_name=r["item_name"],
                day=r["day"],
                description=r["description"],
                amount=r["amount"],
                is_template=0
            ) for r in cur.fetchall()]

        return {
            "incomes": incomes,
            "expenses": expenses,
            "savings": savings
        }
    finally:
        conn.close()

def save_month_fixed_plans(
    year: int,
    month: int,
    incomes: List[FixedPlanItem],
    expenses: List[FixedPlanItem],
    savings: List[FixedPlanItem],
    set_as_default_template: bool = False
):
    with get_db_cursor() as cur:
        # Delete existing month plans
        cur.execute("DELETE FROM fixed_incomes WHERE year = ? AND month = ?", (year, month))
        cur.execute("DELETE FROM fixed_expenses WHERE year = ? AND month = ?", (year, month))
        cur.execute("DELETE FROM savings_investments WHERE year = ? AND month = ?", (year, month))

        # Insert month incomes
        for item in incomes:
            cur.execute("""
                INSERT INTO fixed_incomes (year, month, item_name, expected_day, description, amount, is_template)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (year, month, item.item_name, item.day or "", item.description or "", item.amount))

        # Insert month expenses
        for item in expenses:
            cur.execute("""
                INSERT INTO fixed_expenses (year, month, item_name, withdrawal_day, description, amount, is_template)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (year, month, item.item_name, item.day or "", item.description or "", item.amount))

        # Insert month savings
        for item in savings:
            cur.execute("""
                INSERT INTO savings_investments (year, month, item_name, payment_day, description, amount, is_template)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (year, month, item.item_name, item.day or "", item.description or "", item.amount))

        # If user also wants to update the default template
        if set_as_default_template:
            cur.execute("DELETE FROM fixed_incomes WHERE is_template = 1")
            cur.execute("DELETE FROM fixed_expenses WHERE is_template = 1")
            cur.execute("DELETE FROM savings_investments WHERE is_template = 1")

            for item in incomes:
                cur.execute("""
                    INSERT INTO fixed_incomes (year, month, item_name, expected_day, description, amount, is_template)
                    VALUES (0, 0, ?, ?, ?, ?, 1)
                """, (item.item_name, item.day or "", item.description or "", item.amount))

            for item in expenses:
                cur.execute("""
                    INSERT INTO fixed_expenses (year, month, item_name, withdrawal_day, description, amount, is_template)
                    VALUES (0, 0, ?, ?, ?, ?, 1)
                """, (item.item_name, item.day or "", item.description or "", item.amount))

            for item in savings:
                cur.execute("""
                    INSERT INTO savings_investments (year, month, item_name, payment_day, description, amount, is_template)
                    VALUES (0, 0, ?, ?, ?, ?, 1)
                """, (item.item_name, item.day or "", item.description or "", item.amount))
