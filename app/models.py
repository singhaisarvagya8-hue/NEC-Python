from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False, index=True)  # "income" or "expense"
    category = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, default=date.today, index=True)
    payment_method = Column(String(50), nullable=False, default="Credit Card")
    notes = Column(Text, nullable=True)
    tags = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), unique=True, nullable=False, index=True)
    monthly_limit = Column(Float, nullable=False)
    color = Column(String(20), default="#6366f1")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    billing_cycle = Column(String(20), default="monthly")  # "weekly", "monthly", "yearly"
    category = Column(String(50), nullable=False, default="Entertainment")
    next_billing_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    payment_method = Column(String(50), default="Credit Card")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
