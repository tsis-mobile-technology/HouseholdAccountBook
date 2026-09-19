from app.database.connection import get_db_cursor

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color_hex TEXT NOT NULL DEFAULT '#A8E6CF',
    icon TEXT NOT NULL DEFAULT 'tag',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS variable_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL, -- YYYY-MM-DD
    category_id INTEGER NOT NULL REFERENCES categories(id),
    title TEXT NOT NULL,
    payment_method_id INTEGER NOT NULL REFERENCES payment_methods(id),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    memo TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS fixed_incomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    expected_day TEXT DEFAULT '',
    description TEXT DEFAULT '',
    amount INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
    is_template INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS fixed_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    withdrawal_day TEXT DEFAULT '',
    description TEXT DEFAULT '',
    amount INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
    is_template INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS savings_investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    payment_day TEXT DEFAULT '',
    description TEXT DEFAULT '',
    amount INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
    is_template INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_var_expenses_date ON variable_expenses(transaction_date);
CREATE INDEX IF NOT EXISTS idx_fixed_incomes_ym ON fixed_incomes(year, month);
CREATE INDEX IF NOT EXISTS idx_fixed_expenses_ym ON fixed_expenses(year, month);
CREATE INDEX IF NOT EXISTS idx_savings_ym ON savings_investments(year, month);
"""

DEFAULT_CATEGORIES = [
    ("식비", "#A8E6CF", "utensils", 1),
    ("외식/카페", "#FFD3B6", "coffee", 2),
    ("교통/차량", "#BEE3F8", "car", 3),
    ("생활용품", "#FFF3B0", "shopping-bag", 4),
    ("문화/여가", "#DED2F9", "film", 5),
    ("의료/건강", "#FFB7B2", "heartbeat", 6),
    ("쇼핑/의류", "#E2F0D9", "tshirt", 7),
    ("별콩이", "#FBCFE8", "heart", 8),
    ("기타", "#E2E8F0", "ellipsis-h", 9),
]

DEFAULT_PAYMENTS = [
    ("신용카드", 1),
    ("체크카드", 1),
    ("계좌이체", 1),
    ("현금", 1),
    ("간편결제", 1),
]

# Default templates matching Google Spreadsheet (Default amounts 0 for clean start)
DEFAULT_FIXED_INCOME_TEMPLATES = [
    ("기본급", "25일", "정기 급여", 0),
    ("상여/수당", "-", "성과급 등", 0),
    ("부수입", "-", "이자/배당 등", 0),
    ("기타", "-", "환급금 등", 0),
]

DEFAULT_FIXED_EXPENSE_TEMPLATES = [
    ("주거/관리비", "20일", "관리비 및 공과금", 0),
    ("통신/인터넷", "15일", "휴대폰 및 인터넷", 0),
    ("보장성보험", "10일", "실비 및 암보험", 0),
    ("대출원리금", "25일", "주택담보/신용대출", 0),
    ("구독/회비", "1일", "OTT/멤버십", 0),
    ("기타정기지출", "-", "기타 정기출금", 0),
]

DEFAULT_SAVINGS_TEMPLATES = [
    ("정기적금/예금", "25일", "목돈 마련 적금", 0),
    ("연금저축/IRP", "25일", "세액공제 연금", 0),
    ("주식/ETF투자", "25일", "적립식 투자", 0),
    ("비상금적립", "25일", "CMA 파킹통장", 0),
]

def init_database():
    with get_db_cursor() as cur:
        cur.executescript(SCHEMA_SQL)

        # Seed categories
        for name, color, icon, order in DEFAULT_CATEGORIES:
            cur.execute("""
                INSERT OR IGNORE INTO categories (name, color_hex, icon, sort_order)
                VALUES (?, ?, ?, ?)
            """, (name, color, icon, order))

        # Seed payment methods
        for name, active in DEFAULT_PAYMENTS:
            cur.execute("""
                INSERT OR IGNORE INTO payment_methods (name, is_active)
                VALUES (?, ?)
            """, (name, active))

        # Seed fixed templates (year=0, month=0)
        for item, day, desc, amt in DEFAULT_FIXED_INCOME_TEMPLATES:
            cur.execute("""
                INSERT OR IGNORE INTO fixed_incomes (year, month, item_name, expected_day, description, amount, is_template)
                SELECT 0, 0, ?, ?, ?, ?, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM fixed_incomes WHERE is_template = 1 AND item_name = ?
                )
            """, (item, day, desc, amt, item))

        for item, day, desc, amt in DEFAULT_FIXED_EXPENSE_TEMPLATES:
            cur.execute("""
                INSERT OR IGNORE INTO fixed_expenses (year, month, item_name, withdrawal_day, description, amount, is_template)
                SELECT 0, 0, ?, ?, ?, ?, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM fixed_expenses WHERE is_template = 1 AND item_name = ?
                )
            """, (item, day, desc, amt, item))

        for item, day, desc, amt in DEFAULT_SAVINGS_TEMPLATES:
            cur.execute("""
                INSERT OR IGNORE INTO savings_investments (year, month, item_name, payment_day, description, amount, is_template)
                SELECT 0, 0, ?, ?, ?, ?, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM savings_investments WHERE is_template = 1 AND item_name = ?
                )
            """, (item, day, desc, amt, item))
