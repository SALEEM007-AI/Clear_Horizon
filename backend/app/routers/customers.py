"""
Customers router — list customers and view their history.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, PaymentMethod, Payment, CustomerMethodHistory
from app.schemas import CustomerOut, CustomerHistoryOut, PaymentMethodOut, MethodHistoryOut, PaymentOut

router = APIRouter(prefix="/api", tags=["customers"])


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    """List all customers."""
    return db.query(Customer).order_by(Customer.id).all()


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a single customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/customers/{customer_id}/history", response_model=CustomerHistoryOut)
def get_customer_history(customer_id: int, db: Session = Depends(get_db)):
    """
    Get a customer's full history: payment methods, method history
    (success rates), and recent payments.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    methods = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.customer_id == customer_id)
        .all()
    )

    method_history = (
        db.query(CustomerMethodHistory)
        .filter(CustomerMethodHistory.customer_id == customer_id)
        .all()
    )

    recent_payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer_id)
        .order_by(Payment.created_at.desc())
        .limit(20)
        .all()
    )

    return CustomerHistoryOut(
        customer=CustomerOut.model_validate(customer),
        payment_methods=[PaymentMethodOut.model_validate(m) for m in methods],
        method_history=[MethodHistoryOut.model_validate(h) for h in method_history],
        recent_payments=[PaymentOut.model_validate(p) for p in recent_payments],
    )
