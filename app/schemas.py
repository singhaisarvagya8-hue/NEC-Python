from datetime import date as dt_date, datetime as dt_datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ----------------------
# Transaction Schemas
# ----------------------
class TransactionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    amount: float = Field(..., gt=0)
    type: str = Field(..., pattern="^(income|expense)$")
    category: str = Field(..., min_length=1, max_length=50)
    date: dt_date = Field(default_factory=dt_date.today)
    payment_method: str = Field(default="Credit Card")
    notes: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    amount: Optional[float] = Field(default=None, gt=0)
    type: Optional[str] = Field(default=None, pattern="^(income|expense)$")
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    date: Optional[dt_date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: int
    created_at: Optional[dt_datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------
# Budget Schemas
# ----------------------
class BudgetBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    monthly_limit: float = Field(..., gt=0)
    color: Optional[str] = Field(default="#6366f1")


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    monthly_limit: Optional[float] = Field(default=None, gt=0)
    color: Optional[str] = None


class BudgetResponse(BudgetBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BudgetStatus(BaseModel):
    id: int
    category: str
    monthly_limit: float
    current_spent: float
    remaining: float
    percentage_used: float
    status: str  # "normal", "warning" (>80%), "exceeded" (>100%)
    color: str


# ----------------------
# Subscription Schemas
# ----------------------
class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    billing_cycle: str = Field(default="monthly", pattern="^(weekly|monthly|yearly)$")
    category: str = Field(default="Entertainment")
    next_billing_date: dt_date = Field(...)
    is_active: bool = Field(default=True)
    payment_method: str = Field(default="Credit Card")
    notes: Optional[str] = None


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    billing_cycle: Optional[str] = Field(default=None, pattern="^(weekly|monthly|yearly)$")
    category: Optional[str] = None
    next_billing_date: Optional[dt_date] = None
    is_active: Optional[bool] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    created_at: Optional[dt_datetime] = None
    monthly_equivalent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ----------------------
# Analytics Schemas
# ----------------------
class CategorySpending(BaseModel):
    category: str
    total: float
    percentage: float
    count: int


class MonthlyTrend(BaseModel):
    month: str  # "YYYY-MM"
    income: float
    expense: float
    savings: float


class DailySpending(BaseModel):
    date: str  # "YYYY-MM-DD"
    amount: float


class AnalyticsOverview(BaseModel):
    total_balance: float
    total_income_month: float
    total_expense_month: float
    net_savings_month: float
    savings_rate_month: float
    all_time_income: float
    all_time_expense: float
    daily_average_expense_month: float
    category_breakdown: List[CategorySpending]
    monthly_trends: List[MonthlyTrend]
    daily_spending: List[DailySpending]
    active_subscriptions_cost_monthly: float
    budget_alerts: List[str]
