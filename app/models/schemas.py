from pydantic import BaseModel, Field
from typing import Optional, List

# --- Category & Payment ---
class CategoryModel(BaseModel):
    id: int
    name: str
    color_hex: str
    icon: str
    sort_order: int
    is_active: int

class CategoryCreate(BaseModel):
    name: str
    color_hex: str = "#A8E6CF"
    icon: str = "tag"
    sort_order: int = 0

class PaymentMethodModel(BaseModel):
    id: int
    name: str
    is_active: int

# --- Variable Expense (Daily) ---
class VariableExpenseCreate(BaseModel):
    transaction_date: str = Field(..., description="YYYY-MM-DD")
    category_id: int
    title: str
    payment_method_id: int
    amount: int
    memo: Optional[str] = ""

class VariableExpenseUpdate(BaseModel):
    transaction_date: Optional[str] = None
    category_id: Optional[int] = None
    title: Optional[str] = None
    payment_method_id: Optional[int] = None
    amount: Optional[int] = None
    memo: Optional[str] = None

class VariableExpenseResponse(BaseModel):
    id: int
    transaction_date: str
    category_id: int
    category_name: str
    category_color: str
    category_icon: str
    title: str
    payment_method_id: int
    payment_method_name: str
    amount: int
    memo: Optional[str] = ""
    created_at: str

# --- Fixed Plans (Income, Expense, Savings) ---
class FixedPlanItem(BaseModel):
    id: Optional[int] = None
    year: Optional[int] = 0
    month: Optional[int] = 0
    item_name: str
    day: Optional[str] = ""  # expected_day / withdrawal_day / payment_day
    description: Optional[str] = ""
    amount: int = Field(default=0, ge=0)
    is_template: Optional[int] = 0

class MonthFixedPlansUpdate(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
    incomes: List[FixedPlanItem] = []
    expenses: List[FixedPlanItem] = []
    savings: List[FixedPlanItem] = []
    is_template: Optional[bool] = False

# --- Monthly & Annual Analytics ---
class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    total_income: int           # 고정 수입 합계
    fixed_expense: int          # 고정 지출 합계
    variable_expense: int       # 변동 지출 합계
    total_expense: int          # 총 지출 (고정 + 변동)
    savings_investment: int     # 저축 및 투자
    balance: int                # 당월 잔액 (잉여금 = 수입 - 지출 - 저축)
    savings_rate: float         # 저축률 (%)

class AnnualMonthRow(BaseModel):
    month: int
    month_name: str             # "1월", "2월"...
    total_income: int
    fixed_expense: int
    variable_expense: int
    total_expense: int
    savings_investment: int
    balance: int
    savings_rate: float

class AnnualDashboardResponse(BaseModel):
    year: int
    months: List[AnnualMonthRow]
    annual_total: AnnualMonthRow
    monthly_average: AnnualMonthRow

# --- Mobile Quick Overview ---
class MobileOverviewResponse(BaseModel):
    today_date: str
    today_expense_total: int
    today_transaction_count: int
    month_summary: MonthlySummaryResponse
    recent_transactions: List[VariableExpenseResponse]

# --- Card Statement Import & Deduplication ---
class CardParsedItem(BaseModel):
    temp_id: str
    transaction_date: str
    title: str
    amount: int
    category_id: int
    category_name: str
    payment_method_id: int
    payment_method_name: str
    installment: str = ""
    memo: str = ""
    is_duplicate: bool = False
    duplicate_reason: str = ""
    existing_expense_id: Optional[int] = None
    action: str = "add_new"  # add_new | merge | skip

class CardPreviewResponse(BaseModel):
    issuer: str
    issuer_name: str
    filename: str
    statement_month: Optional[str] = ""
    total_count: int
    total_amount: int
    duplicate_count: int
    items: List[CardParsedItem]

class CardConfirmItem(BaseModel):
    action: str = "add_new"  # add_new | merge | skip
    transaction_date: str
    category_id: int
    payment_method_id: int
    title: str
    amount: int
    memo: Optional[str] = ""
    existing_expense_id: Optional[int] = None

class CardConfirmRequest(BaseModel):
    items: List[CardConfirmItem]

class CardConfirmResponse(BaseModel):
    status: str
    added: int
    merged: int
    skipped: int
    total: int
    message: str

# --- Monthly Spending Pattern Analytics ---
class CategorySpendingItem(BaseModel):
    category_id: int
    name: str
    color_hex: str
    icon: str
    amount: int
    percentage: float
    prev_amount: int
    diff_amount: int
    diff_rate: float
    count: int

class PaymentMethodSpendingItem(BaseModel):
    payment_method_id: int
    name: str
    amount: int
    count: int
    percentage: float

class WeeklySpendingItem(BaseModel):
    week_num: int
    week_label: str
    amount: int
    count: int

class DayOfWeekSpendingItem(BaseModel):
    day_name: str
    amount: int
    count: int

class TopMerchantItem(BaseModel):
    rank: int
    merchant: str
    amount: int
    count: int
    percentage: float
    category_name: str

class SpendingPatternsResponse(BaseModel):
    year: int
    month: int
    total_spending: int
    prev_total_spending: int
    spending_diff: int
    spending_diff_rate: float
    daily_average: int
    transaction_count: int
    avg_per_transaction: int
    no_spend_days: int
    peak_spending_date: Optional[str] = None
    peak_spending_amount: int = 0
    weekday_spending: int = 0
    weekend_spending: int = 0
    weekday_avg: int = 0
    weekend_avg: int = 0
    insight_summary: str = ""
    categories: List[CategorySpendingItem]
    payment_methods: List[PaymentMethodSpendingItem]
    weekly: List[WeeklySpendingItem]
    day_of_week: List[DayOfWeekSpendingItem]
    top_merchants: List[TopMerchantItem]

