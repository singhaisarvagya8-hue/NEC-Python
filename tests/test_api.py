import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Create in-memory SQLite database specifically for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh tables before each test and drop afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_and_read_transaction():
    """Verify transaction creation and retrieval."""
    payload = {
        "title": "Grocery Shopping",
        "amount": 75.50,
        "type": "expense",
        "category": "Food & Dining",
        "date": str(date.today()),
        "payment_method": "Credit Card",
        "notes": "Weekly produce",
        "tags": "groceries",
    }
    create_res = client.post("/api/transactions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["id"] is not None
    assert created_data["amount"] == 75.50
    assert created_data["title"] == "Grocery Shopping"

    # Read back list
    list_res = client.get("/api/transactions")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["title"] == "Grocery Shopping"


def test_filter_and_search_transactions():
    """Verify filtering by type, category, and text search."""
    t1 = {
        "title": "Tech Salary",
        "amount": 5000.0,
        "type": "income",
        "category": "Salary",
        "date": str(date.today()),
    }
    t2 = {
        "title": "Apartment Rent",
        "amount": 1200.0,
        "type": "expense",
        "category": "Housing & Rent",
        "date": str(date.today()),
    }
    client.post("/api/transactions", json=t1)
    client.post("/api/transactions", json=t2)

    # Filter income only
    income_res = client.get("/api/transactions?trans_type=income")
    assert len(income_res.json()) == 1
    assert income_res.json()[0]["title"] == "Tech Salary"

    # Filter expense only
    expense_res = client.get("/api/transactions?trans_type=expense")
    assert len(expense_res.json()) == 1
    assert expense_res.json()[0]["title"] == "Apartment Rent"

    # Search by keyword
    search_res = client.get("/api/transactions?search=Rent")
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["title"] == "Apartment Rent"


def test_update_and_delete_transaction():
    """Verify transaction updating and deletion."""
    payload = {
        "title": "Coffee",
        "amount": 4.50,
        "type": "expense",
        "category": "Food & Dining",
        "date": str(date.today()),
    }
    create_res = client.post("/api/transactions", json=payload)
    t_id = create_res.json()["id"]

    # Update amount
    update_res = client.put(f"/api/transactions/{t_id}", json={"amount": 5.50, "title": "Specialty Coffee"})
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 5.50
    assert update_res.json()["title"] == "Specialty Coffee"

    # Delete
    del_res = client.delete(f"/api/transactions/{t_id}")
    assert del_res.status_code == 200

    # Ensure 404 when querying deleted item
    get_res = client.get(f"/api/transactions/{t_id}")
    assert get_res.status_code == 404


def test_budget_status_and_alerts():
    """Verify budget creation and calculation of normal, warning, and exceeded states."""
    # Set Budget for Food & Dining = $100
    budget_payload = {
        "category": "Food & Dining",
        "monthly_limit": 100.0,
        "color": "#f59e0b",
    }
    b_res = client.post("/api/budgets", json=budget_payload)
    assert b_res.status_code == 200

    # Add expense of $85 (85% => warning threshold)
    client.post(
        "/api/transactions",
        json={
            "title": "Dinner with friends",
            "amount": 85.0,
            "type": "expense",
            "category": "Food & Dining",
            "date": str(date.today()),
        },
    )

    status_res = client.get("/api/budgets/status")
    assert status_res.status_code == 200
    statuses = status_res.json()
    assert len(statuses) == 1
    assert statuses[0]["category"] == "Food & Dining"
    assert statuses[0]["percentage_used"] == 85.0
    assert statuses[0]["status"] == "warning"

    # Add another $20 expense (total $105 => exceeded threshold)
    client.post(
        "/api/transactions",
        json={
            "title": "Snacks",
            "amount": 20.0,
            "type": "expense",
            "category": "Food & Dining",
            "date": str(date.today()),
        },
    )

    status_res2 = client.get("/api/budgets/status")
    statuses2 = status_res2.json()
    assert statuses2[0]["current_spent"] == 105.0
    assert statuses2[0]["percentage_used"] == 105.0
    assert statuses2[0]["status"] == "exceeded"


def test_subscriptions_and_quick_pay():
    """Verify subscription lifecycle and logging payment as expense."""
    sub_payload = {
        "name": "Cloud Storage",
        "amount": 9.99,
        "billing_cycle": "monthly",
        "category": "Utilities & Bills",
        "next_billing_date": str(date.today()),
        "payment_method": "Credit Card",
    }
    sub_res = client.post("/api/subscriptions", json=sub_payload)
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]
    assert sub_res.json()["monthly_equivalent"] == 9.99

    # Trigger quick pay
    pay_res = client.post(f"/api/subscriptions/{sub_id}/pay")
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    assert pay_data["amount"] == 9.99
    assert pay_data["type"] == "expense"
    assert "Cloud Storage" in pay_data["title"]


def test_analytics_overview():
    """Verify aggregated financial analytics overview."""
    today = date.today()
    # Salary
    client.post("/api/transactions", json={
        "title": "Salary", "amount": 3000.0, "type": "income", "category": "Salary", "date": str(today)
    })
    # Rent
    client.post("/api/transactions", json={
        "title": "Rent", "amount": 1000.0, "type": "expense", "category": "Housing & Rent", "date": str(today)
    })

    overview_res = client.get("/api/analytics/overview")
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert data["total_income_month"] == 3000.0
    assert data["total_expense_month"] == 1000.0
    assert data["net_savings_month"] == 2000.0
    assert data["savings_rate_month"] == pytest.approx(66.7, 0.1)


def test_csv_export():
    """Verify CSV export response."""
    client.post("/api/transactions", json={
        "title": "Test Item", "amount": 25.0, "type": "expense", "category": "Other", "date": str(date.today())
    })
    csv_res = client.get("/api/transactions/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Test Item" in csv_res.text
