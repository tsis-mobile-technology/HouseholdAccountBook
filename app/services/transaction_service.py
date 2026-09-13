from datetime import datetime
from typing import List, Optional, Tuple
from app.database.connection import get_connection, get_db_cursor
from app.models.schemas import VariableExpenseCreate, VariableExpenseUpdate, VariableExpenseResponse

def create_variable_expense(data: VariableExpenseCreate) -> int:
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO variable_expenses (transaction_date, category_id, title, payment_method_id, amount, memo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data.transaction_date, data.category_id, data.title, data.payment_method_id, data.amount, data.memo or ""))
        return cur.lastrowid

def update_variable_expense(expense_id: int, data: VariableExpenseUpdate) -> bool:
    fields = []
    values = []
    if data.transaction_date is not None:
        fields.append("transaction_date = ?")
        values.append(data.transaction_date)
    if data.category_id is not None:
        fields.append("category_id = ?")
        values.append(data.category_id)
    if data.title is not None:
        fields.append("title = ?")
        values.append(data.title)
    if data.payment_method_id is not None:
        fields.append("payment_method_id = ?")
        values.append(data.payment_method_id)
    if data.amount is not None:
        fields.append("amount = ?")
        values.append(data.amount)
    if data.memo is not None:
        fields.append("memo = ?")
        values.append(data.memo)

    if not fields:
        return False

    fields.append("updated_at = datetime('now', 'localtime')")
    values.append(expense_id)

    with get_db_cursor() as cur:
        cur.execute(f"UPDATE variable_expenses SET {', '.join(fields)} WHERE id = ?", values)
        return cur.rowcount > 0

def delete_variable_expense(expense_id: int) -> bool:
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM variable_expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0

def get_variable_expenses(
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[int] = None,
    limit: int = 500
) -> List[VariableExpenseResponse]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT 
                v.id, v.transaction_date, v.category_id, c.name as category_name,
                c.color_hex as category_color, c.icon as category_icon,
                v.title, v.payment_method_id, p.name as payment_method_name,
                v.amount, v.memo, v.created_at
            FROM variable_expenses v
            JOIN categories c ON v.category_id = c.id
            JOIN payment_methods p ON v.payment_method_id = p.id
            WHERE 1=1
        """
        params = []
        if year and month:
            prefix = f"{year:04d}-{month:02d}%"
            query += " AND v.transaction_date LIKE ?"
            params.append(prefix)
        elif year:
            prefix = f"{year:04d}%"
            query += " AND v.transaction_date LIKE ?"
            params.append(prefix)

        if start_date:
            query += " AND v.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND v.transaction_date <= ?"
            params.append(end_date)
        if category_id:
            query += " AND v.category_id = ?"
            params.append(category_id)

        query += " ORDER BY v.transaction_date DESC, v.id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        return [
            VariableExpenseResponse(
                id=r["id"],
                transaction_date=r["transaction_date"],
                category_id=r["category_id"],
                category_name=r["category_name"],
                category_color=r["category_color"],
                category_icon=r["category_icon"],
                title=r["title"],
                payment_method_id=r["payment_method_id"],
                payment_method_name=r["payment_method_name"],
                amount=r["amount"],
                memo=r["memo"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()

def get_today_summary(today_date_str: str) -> Tuple[int, int]:
    """Returns (today_total_amount, today_count)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(id) as count
            FROM variable_expenses
            WHERE transaction_date = ?
        """, (today_date_str,))
        row = cur.fetchone()
        return (row["total"], row["count"])
    finally:
        conn.close()
