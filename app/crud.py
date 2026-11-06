from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
import csv
import io

from app import models, schemas


# ============================================================================
# TRANSACTIONS CRUD
# ============================================================================

def get_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    trans_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
) -> List[models.Transaction]:
    query = db.query(models.Transaction)

    if trans_type:
        query = query.filter(models.Transaction.type == trans_type)
    if category:
        query = query.filter(models.Transaction.category == category)
    if start_date:
        query = query.filter(models.Transaction.date >= start_date)
    if end_date:
        query = query.filter(models.Transaction.date <= end_date)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                models.Transaction.title.ilike(search_fmt),
                models.Transaction.notes.ilike(search_fmt),
                models.Transaction.tags.ilike(search_fmt),
                models.Transaction.category.ilike(search_fmt),
            )
        )

    return query.order_by(models.Transaction.date.desc(), models.Transaction.id.desc()).offset(skip).limit(limit).all()


def get_transaction(db: Session, transaction_id: int) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()


def create_transaction(db: Session, transaction_in: schemas.TransactionCreate) -> models.Transaction:
    db_item = models.Transaction(**transaction_in.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_transaction(
    db: Session, transaction_id: int, transaction_in: schemas.TransactionUpdate
) -> Optional[models.Transaction]:
    db_item = get_transaction(db, transaction_id)
    if not db_item:
        return None

    update_data = transaction_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_item, field, val)

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_transaction(db: Session, transaction_id: int) -> bool:
    db_item = get_transaction(db, transaction_id)
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True


# ============================================================================
# BUDGETS CRUD
# ============================================================================

def get_budgets(db: Session) -> List[models.Budget]:
    return db.query(models.Budget).order_by(models.Budget.category.asc()).all()


def get_budget_by_category(db: Session, category: str) -> Optional[models.Budget]:
    return db.query(models.Budget).filter(models.Budget.category == category).first()


def create_or_update_budget(db: Session, budget_in: schemas.BudgetCreate) -> models.Budget:
    existing = get_budget_by_category(db, budget_in.category)
    if existing:
        existing.monthly_limit = budget_in.monthly_limit
        if budget_in.color:
            existing.color = budget_in.color
        db.commit()
        db.refresh(existing)
        return existing

    db_budget = models.Budget(**budget_in.model_dump())
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


def delete_budget(db: Session, budget_id: int) -> bool:
    db_budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not db_budget:
        return False
    db.delete(db_budget)
    db.commit()
    return True


def get_budget_statuses(db: Session, year: int, month: int) -> List[schemas.BudgetStatus]:
    budgets = get_budgets(db)
    results = []

    for b in budgets:
        # Sum expenses in this category for given year and month
        spent_query = db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).filter(
            models.Transaction.type == "expense",
            models.Transaction.category == b.category,
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        current_spent = float(spent_query.scalar() or 0.0)
        percentage = round((current_spent / b.monthly_limit) * 100, 1) if b.monthly_limit > 0 else 0.0
        remaining = round(b.monthly_limit - current_spent, 2)

        if percentage >= 100:
            status = "exceeded"
        elif percentage >= 80:
            status = "warning"
        else:
            status = "normal"

        results.append(
            schemas.BudgetStatus(
                id=b.id,
                category=b.category,
                monthly_limit=round(b.monthly_limit, 2),
                current_spent=round(current_spent, 2),
                remaining=remaining,
                percentage_used=percentage,
                status=status,
                color=b.color or "#6366f1",
            )
        )

    return sorted(results, key=lambda x: x.percentage_used, reverse=True)


# ============================================================================
# SUBSCRIPTIONS CRUD
# ============================================================================

def normalize_subscription_monthly(amount: float, cycle: str) -> float:
    cycle = cycle.lower()
    if cycle == "weekly":
        return round(amount * (52 / 12), 2)
    elif cycle == "yearly":
        return round(amount / 12, 2)
    return round(amount, 2)


def get_subscriptions(db: Session, active_only: bool = False) -> List[schemas.SubscriptionResponse]:
    query = db.query(models.Subscription)
    if active_only:
        query = query.filter(models.Subscription.is_active.is_(True))
    subs = query.order_by(models.Subscription.next_billing_date.asc()).all()

    response_list = []
    for s in subs:
        resp = schemas.SubscriptionResponse.model_validate(s)
        resp.monthly_equivalent = normalize_subscription_monthly(s.amount, s.billing_cycle)
        response_list.append(resp)
    return response_list


def create_subscription(db: Session, sub_in: schemas.SubscriptionCreate) -> schemas.SubscriptionResponse:
    db_sub = models.Subscription(**sub_in.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    resp = schemas.SubscriptionResponse.model_validate(db_sub)
    resp.monthly_equivalent = normalize_subscription_monthly(db_sub.amount, db_sub.billing_cycle)
    return resp


def update_subscription(
    db: Session, sub_id: int, sub_in: schemas.SubscriptionUpdate
) -> Optional[schemas.SubscriptionResponse]:
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        return None

    for field, val in sub_in.model_dump(exclude_unset=True).items():
        setattr(db_sub, field, val)

    db.commit()
    db.refresh(db_sub)
    resp = schemas.SubscriptionResponse.model_validate(db_sub)
    resp.monthly_equivalent = normalize_subscription_monthly(db_sub.amount, db_sub.billing_cycle)
    return resp


def delete_subscription(db: Session, sub_id: int) -> bool:
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        return False
    db.delete(db_sub)
    db.commit()
    return True


# ============================================================================
# ANALYTICS & INSIGHTS
# ============================================================================

def get_analytics_overview(db: Session, year: Optional[int] = None, month: Optional[int] = None) -> schemas.AnalyticsOverview:
    today = date.today()
    if not year:
        year = today.year
    if not month:
        month = today.month

    # 1. Month Income and Expense
    month_income = float(
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.type == "income",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .scalar()
    )

    month_expense = float(
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.type == "expense",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .scalar()
    )

    # 2. All-Time Income and Expense
    all_income = float(
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(models.Transaction.type == "income")
        .scalar()
    )

    all_expense = float(
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(models.Transaction.type == "expense")
        .scalar()
    )

    total_balance = round(all_income - all_expense, 2)
    net_savings_month = round(month_income - month_expense, 2)
    savings_rate_month = round((net_savings_month / month_income) * 100, 1) if month_income > 0 else 0.0

    # Daily Average for Month
    # Days elapsed in current month or total days
    days_in_month = (date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1) - timedelta(days=1)).day
    divisor = today.day if (year == today.year and month == today.month) else days_in_month
    divisor = max(1, divisor)
    daily_average_expense_month = round(month_expense / divisor, 2)

    # 3. Category Breakdown for current month
    cat_query = (
        db.query(
            models.Transaction.category,
            func.sum(models.Transaction.amount).label("total"),
            func.count(models.Transaction.id).label("cnt"),
        )
        .filter(
            models.Transaction.type == "expense",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .group_by(models.Transaction.category)
        .order_by(func.sum(models.Transaction.amount).desc())
        .all()
    )

    category_breakdown = []
    for cat, total, cnt in cat_query:
        pct = round((total / month_expense) * 100, 1) if month_expense > 0 else 0.0
        category_breakdown.append(
            schemas.CategorySpending(category=cat, total=round(total, 2), percentage=pct, count=cnt)
        )

    # 4. Monthly Trends (last 6 months)
    monthly_trends = []
    for i in range(5, -1, -1):
        # Calculate target year and month
        target_month = month - i
        target_year = year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        inc = float(
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
                models.Transaction.type == "income",
                extract("year", models.Transaction.date) == target_year,
                extract("month", models.Transaction.date) == target_month,
            )
            .scalar()
        )

        exp = float(
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
                models.Transaction.type == "expense",
                extract("year", models.Transaction.date) == target_year,
                extract("month", models.Transaction.date) == target_month,
            )
            .scalar()
        )

        label = f"{target_year}-{target_month:02d}"
        monthly_trends.append(
            schemas.MonthlyTrend(
                month=label,
                income=round(inc, 2),
                expense=round(exp, 2),
                savings=round(inc - exp, 2),
            )
        )

    # 5. Daily Spending for the selected month
    daily_query = (
        db.query(
            models.Transaction.date,
            func.sum(models.Transaction.amount).label("total"),
        )
        .filter(
            models.Transaction.type == "expense",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .group_by(models.Transaction.date)
        .order_by(models.Transaction.date.asc())
        .all()
    )

    daily_spending = [
        schemas.DailySpending(date=d.strftime("%Y-%m-%d"), amount=round(tot, 2))
        for d, tot in daily_query
    ]

    # 6. Active Subscriptions Monthly Cost
    active_subs = get_subscriptions(db, active_only=True)
    subs_monthly = sum(s.monthly_equivalent for s in active_subs)

    # 7. Budget Alerts
    budget_statuses = get_budget_statuses(db, year, month)
    alerts = []
    for b in budget_statuses:
        if b.status == "exceeded":
            alerts.append(f"⚠️ Budget exceeded for '{b.category}': ${b.current_spent:.2f} spent of ${b.monthly_limit:.2f} limit (+{b.percentage_used - 100:.1f}%)")
        elif b.status == "warning":
            alerts.append(f"⚡ Warning: '{b.category}' has reached {b.percentage_used:.1f}% of limit (${b.current_spent:.2f} of ${b.monthly_limit:.2f})")

    return schemas.AnalyticsOverview(
        total_balance=total_balance,
        total_income_month=round(month_income, 2),
        total_expense_month=round(month_expense, 2),
        net_savings_month=net_savings_month,
        savings_rate_month=savings_rate_month,
        all_time_income=round(all_income, 2),
        all_time_expense=round(all_expense, 2),
        daily_average_expense_month=daily_average_expense_month,
        category_breakdown=category_breakdown,
        monthly_trends=monthly_trends,
        daily_spending=daily_spending,
        active_subscriptions_cost_monthly=round(subs_monthly, 2),
        budget_alerts=alerts,
    )


# ============================================================================
# CSV EXPORT
# ============================================================================

def export_transactions_to_csv(db: Session) -> str:
    transactions = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Title", "Type", "Category", "Amount", "Payment Method", "Notes", "Tags"])

    for t in transactions:
        writer.writerow([
            t.id,
            t.date.strftime("%Y-%m-%d"),
            t.title,
            t.type,
            t.category,
            f"{t.amount:.2f}",
            t.payment_method,
            t.notes or "",
            t.tags or "",
        ])

    return output.getvalue()
