from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, crud, models

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=List[schemas.SubscriptionResponse])
def read_subscriptions(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List recurring subscriptions and memberships with monthly cost normalization."""
    return crud.get_subscriptions(db=db, active_only=active_only)


@router.post("", response_model=schemas.SubscriptionResponse, status_code=201)
def create_new_subscription(
    sub_in: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
):
    """Add a new recurring subscription."""
    return crud.create_subscription(db=db, sub_in=sub_in)


@router.put("/{sub_id}", response_model=schemas.SubscriptionResponse)
def update_subscription(
    sub_id: int,
    sub_in: schemas.SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    """Update subscription details or status."""
    updated = crud.update_subscription(db=db, sub_id=sub_id, sub_in=sub_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated


@router.delete("/{sub_id}")
def delete_subscription(sub_id: int, db: Session = Depends(get_db)):
    """Delete a subscription."""
    deleted = crud.delete_subscription(db=db, sub_id=sub_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"status": "success", "message": "Subscription deleted successfully"}


@router.post("/{sub_id}/pay", response_model=schemas.TransactionResponse)
def log_subscription_payment(sub_id: int, db: Session = Depends(get_db)):
    """Quick-log a subscription payment as an expense transaction for today."""
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    trans_in = schemas.TransactionCreate(
        title=f"Subscription: {sub.name}",
        amount=sub.amount,
        type="expense",
        category=sub.category or "Entertainment",
        date=date.today(),
        payment_method=sub.payment_method or "Credit Card",
        notes=f"Recurring {sub.billing_cycle} payment for {sub.name}",
        tags="subscription,recurring",
    )
    return crud.create_transaction(db=db, transaction_in=trans_in)
