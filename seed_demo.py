"""FinTrack Pro - Standalone Demo Data Seeder CLI.

Run this script to initialize the database with 3 months of realistic
income, expense transactions, monthly budgets, and recurring subscriptions.
"""

from app.database import SessionLocal, Base, engine
from app.routers.analytics import seed_demo_data


def main():
    print("🚀 Initializing FinTrack Pro database schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("🌱 Seeding realistic demo data (transactions, budgets, subscriptions)...")
        res = seed_demo_data(db=db)
        print(f"✅ Success: {res['message']}")
        print("💡 You can now start the application with: uvicorn app.main:app --reload")
    finally:
        db.close()


if __name__ == "__main__":
    main()
