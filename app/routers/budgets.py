from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])


@router.get("", response_model=List[schemas.BudgetResponse])
def read_budgets(db: Session = Depends(get_db)):
    """Retrieve all category budgets."""
    return crud.get_budgets(db=db)


@router.post("", response_model=schemas.BudgetResponse)
def upsert_budget(
    budget_in: schemas.BudgetCreate,
    db: Session = Depends(get_db),
):
    """Create or update a category budget limit."""
    return crud.create_or_update_budget(db=db, budget_in=budget_in)


@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """Delete a budget by ID."""
    deleted = crud.delete_budget(db=db, budget_id=budget_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"status": "success", "message": "Budget deleted successfully"}


@router.get("/status", response_model=List[schemas.BudgetStatus])
def get_budget_statuses(
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (default: current month)"),
    db: Session = Depends(get_db),
):
    """Get active budget statuses with spent amount, remaining balance, and usage percentage."""
    today = date.today()
    y = year or today.year
    m = month or today.month
    return crud.get_budget_statuses(db=db, year=y, month=m)
