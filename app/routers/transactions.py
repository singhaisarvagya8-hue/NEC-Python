from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=List[schemas.TransactionResponse])
def read_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    trans_type: Optional[str] = Query(None, pattern="^(income|expense)$"),
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve transactions with comprehensive filtering, search, and pagination."""
    return crud.get_transactions(
        db=db,
        skip=skip,
        limit=limit,
        trans_type=trans_type,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


@router.post("", response_model=schemas.TransactionResponse, status_code=201)
def create_new_transaction(
    transaction_in: schemas.TransactionCreate,
    db: Session = Depends(get_db),
):
    """Create a new income or expense transaction."""
    return crud.create_transaction(db=db, transaction_in=transaction_in)


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """Export all transactions as a downloadable CSV file."""
    csv_data = crud.export_transactions_to_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fintrack_transactions.csv"},
    )


@router.get("/{transaction_id}", response_model=schemas.TransactionResponse)
def read_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve details of a single transaction by ID."""
    t = crud.get_transaction(db=db, transaction_id=transaction_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_existing_transaction(
    transaction_id: int,
    transaction_in: schemas.TransactionUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing transaction."""
    updated = crud.update_transaction(db=db, transaction_id=transaction_id, transaction_in=transaction_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated


@router.delete("/{transaction_id}")
def delete_existing_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Delete a transaction by ID."""
    deleted = crud.delete_transaction(db=db, transaction_id=transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": "success", "message": "Transaction deleted successfully"}
