import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'fintrack.db'}")
APP_TITLE = "FinTrack Pro - Smart Personal Finance & Expense Analytics"
APP_DESCRIPTION = "A modern, full-featured personal finance manager with budgets, recurring subscriptions, and visual analytics."
APP_VERSION = "1.0.0"
