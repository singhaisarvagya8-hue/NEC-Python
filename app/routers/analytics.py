from datetime import date, timedelta
import random
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud, models

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/overview", response_model=schemas.AnalyticsOverview)
def get_analytics(
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (default: current month)"),
    db: Session = Depends(get_db),
):
    """Retrieve complete financial metrics, category breakdowns, 6-month trends, and budget alerts."""
    return crud.get_analytics_overview(db=db, year=year, month=month)


@router.post("/seed-demo")
def seed_demo_data(db: Session = Depends(get_db)):
    """Seed realistic transactions, budgets, and subscriptions for instant demo and visual testing."""
    today = date.today()

    # Clear existing demo transactions/budgets/subscriptions if any
    db.query(models.Transaction).delete()
    db.query(models.Budget).delete()
    db.query(models.Subscription).delete()
    db.commit()

    # 1. Create Default Budgets
    default_budgets = [
        {"category": "Food & Dining", "monthly_limit": 600.0, "color": "#f59e0b"},
        {"category": "Housing & Rent", "monthly_limit": 1400.0, "color": "#6366f1"},
        {"category": "Shopping", "monthly_limit": 300.0, "color": "#ec4899"},
        {"category": "Transportation", "monthly_limit": 250.0, "color": "#06b6d4"},
        {"category": "Utilities & Bills", "monthly_limit": 200.0, "color": "#8b5cf6"},
        {"category": "Entertainment", "monthly_limit": 180.0, "color": "#10b981"},
        {"category": "Healthcare", "monthly_limit": 150.0, "color": "#ef4444"},
    ]
    for b in default_budgets:
        crud.create_or_update_budget(db, schemas.BudgetCreate(**b))

    # 2. Create Active Subscriptions
    sample_subs = [
        {
            "name": "Netflix Premium",
            "amount": 19.99,
            "billing_cycle": "monthly",
            "category": "Entertainment",
            "next_billing_date": today + timedelta(days=12),
            "payment_method": "Credit Card",
            "notes": "4K streaming plan",
        },
        {
            "name": "Spotify Family",
            "amount": 16.99,
            "billing_cycle": "monthly",
            "category": "Entertainment",
            "next_billing_date": today + timedelta(days=5),
            "payment_method": "Credit Card",
            "notes": "Music streaming",
        },
        {
            "name": "Gym & Fitness Club",
            "amount": 49.00,
            "billing_cycle": "monthly",
            "category": "Healthcare",
            "next_billing_date": today + timedelta(days=18),
            "payment_method": "Debit Card",
            "notes": "All access pass",
        },
        {
            "name": "GitHub Copilot / Cloud",
            "amount": 10.00,
            "billing_cycle": "monthly",
            "category": "Utilities & Bills",
            "next_billing_date": today + timedelta(days=22),
            "payment_method": "Credit Card",
            "notes": "Developer tools",
        },
        {
            "name": "Amazon Prime",
            "amount": 139.00,
            "billing_cycle": "yearly",
            "category": "Shopping",
            "next_billing_date": today + timedelta(days=120),
            "payment_method": "Credit Card",
            "notes": "Annual delivery & video perk",
        },
    ]
    for s in sample_subs:
        crud.create_subscription(db, schemas.SubscriptionCreate(**s))

    # 3. Create 3 Months of Realistic Transactions (Current month, M-1, M-2)
    categories_data = [
        ("Food & Dining", ["Whole Foods Market", "Trader Joe's", "Chipotle Dinner", "Coffee & Pastries", "Sushi Lunch", "Local Pizzeria"], 12.0, 85.0),
        ("Housing & Rent", ["Monthly Apartment Rent"], 1350.0, 1350.0),
        ("Transportation", ["Metro Transit Pass", "Uber Ride", "Gasoline Fuel", "Car Maintenance"], 15.0, 65.0),
        ("Utilities & Bills", ["Electric & Power Utility", "High-Speed Internet", "Water Bill"], 40.0, 95.0),
        ("Shopping", ["Winter Jacket", "Books & Stationery", "Home Essentials", "Tech Accessories"], 25.0, 120.0),
        ("Entertainment", ["Movie Tickets", "Concert Pass", "Video Game Purchase", "Board Game Cafe"], 18.0, 75.0),
        ("Healthcare", ["Pharmacy Prescription", "Dental Checkup Copay", "Vitamins & Supplements"], 20.0, 60.0),
    ]

    methods = ["Credit Card", "Debit Card", "UPI", "Bank Transfer", "Cash"]

    # Generate historical data for past 75 days
    for day_offset in range(75, -1, -1):
        trans_date = today - timedelta(days=day_offset)

        # 1st of the month: Salary paycheck
        if trans_date.day == 1:
            crud.create_transaction(
                db,
                schemas.TransactionCreate(
                    title="Monthly Salary Deposit",
                    amount=4500.0,
                    type="income",
                    category="Salary",
                    date=trans_date,
                    payment_method="Bank Transfer",
                    notes="Direct payroll deposit from employer",
                    tags="salary,income,primary",
                ),
            )
            # Rent payment on the 1st
            crud.create_transaction(
                db,
                schemas.TransactionCreate(
                    title="Monthly Apartment Rent",
                    amount=1350.0,
                    type="expense",
                    category="Housing & Rent",
                    date=trans_date,
                    payment_method="Bank Transfer",
                    notes="Apartment lease payment",
                    tags="rent,fixed",
                ),
            )

        # Mid-month bonus / freelance income (around 15th)
        if trans_date.day == 15:
            crud.create_transaction(
                db,
                schemas.TransactionCreate(
                    title="Freelance Design / Consulting",
                    amount=650.0,
                    type="income",
                    category="Investment",
                    date=trans_date,
                    payment_method="Bank Transfer",
                    notes="Client contract project deliverable",
                    tags="freelance,side-income",
                ),
            )

        # Random expenses on ~40% of days
        if random.random() < 0.45:
            cat, items, min_val, max_val = random.choice(categories_data)
            item = random.choice(items)
            amount = round(random.uniform(min_val, max_val), 2)
            method = random.choice(methods)
            crud.create_transaction(
                db,
                schemas.TransactionCreate(
                    title=item,
                    amount=amount,
                    type="expense",
                    category=cat,
                    date=trans_date,
                    payment_method=method,
                    notes=f"Sample expense for {item}",
                    tags=f"{cat.lower().replace(' ', '-')}",
                ),
            )

    return {
        "status": "success",
        "message": "Demo data seeded successfully with realistic 3-month transactions, budgets, and subscriptions!",
    }
