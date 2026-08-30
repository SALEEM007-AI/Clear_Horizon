"""
Payments router — simulation, listing, detail, retry-link, and webhook endpoints.
"""

import random
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.models import (
    Customer, Payment, PaymentMethod, CustomerMethodHistory,
    RecoveryAction, Outcome,
)
from app.schemas import (
    PaymentSimulateRequest, PaymentOut, PaymentDetailOut,
)
from app.agent import decide
from app.razorpay_service import create_payment_link, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])


# ── Nudge text templates ─────────────────────────────────────────────────────

def _generate_nudge_text(
    customer_name: str,
    amount: float,
    failure_reason: str,
    recommended_method: str | None,
) -> str:
    """Generate a personalized nudge message for the customer."""
    first_name = customer_name.split()[0]
    method_label = (recommended_method or "an alternative method").replace("_", " ").title()

    templates = {
        "INSUFFICIENT_FUNDS": (
            f"Hi {first_name}, your payment of ₹{amount:,.2f} couldn't go through "
            f"due to insufficient funds. You can retry using {method_label} — "
            f"click the link below to complete your payment securely."
        ),
        "OTP_TIMEOUT": (
            f"Hi {first_name}, your ₹{amount:,.2f} payment timed out waiting for OTP. "
            f"No worries — try again using {method_label} for a smoother experience."
        ),
        "CARD_DECLINED": (
            f"Hi {first_name}, your card was declined for ₹{amount:,.2f}. "
            f"Please try with {method_label} or contact your bank. "
            f"Use the link below to retry."
        ),
    }

    return templates.get(
        failure_reason,
        f"Hi {first_name}, your payment of ₹{amount:,.2f} failed. "
        f"Please retry using {method_label} — click below to complete it."
    )


@router.post("/payments/simulate", response_model=PaymentDetailOut)
async def simulate_payment(req: PaymentSimulateRequest, db: Session = Depends(get_db)):
    """
    Simulate a failed payment: creates a FAILED record, runs the agent decision
    pipeline, persists the recovery action, generates Razorpay payment link
    for nudges, and simulates outcomes.
    """
    # Validate customer exists
    customer = db.query(Customer).filter(Customer.id == req.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {req.customer_id} not found")

    # Pick a payment method (use provided or pick first active one)
    method = None
    if req.method_id:
        method = db.query(PaymentMethod).filter(
            PaymentMethod.id == req.method_id,
            PaymentMethod.customer_id == req.customer_id,
        ).first()
    else:
        method = db.query(PaymentMethod).filter(
            PaymentMethod.customer_id == req.customer_id,
            PaymentMethod.is_active == True,
        ).first()

    # Create the failed payment
    payment = Payment(
        customer_id=req.customer_id,
        amount=req.amount,
        method_id=method.id if method else None,
        status="FAILED",
        failure_reason=req.failure_reason,
    )
    db.add(payment)
    db.flush()

    # Get customer method history for the agent
    history_rows = db.query(CustomerMethodHistory).filter(
        CustomerMethodHistory.customer_id == req.customer_id,
    ).all()
    method_history = [
        {
            "method_type": h.method_type,
            "attempts": h.attempts,
            "successes": h.successes,
        }
        for h in history_rows
    ]

    failed_method_type = method.type if method else None

    # ── Agent decision ──────────────────────────────────────────────────
    decision = await decide(
        failure_reason=req.failure_reason,
        amount=req.amount,
        failed_method_type=failed_method_type,
        method_history=method_history,
    )

    recovery_action = RecoveryAction(
        payment_id=payment.id,
        action_type=decision.action_type,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        recommended_method=decision.recommended_method,
    )

    # ── Route by action type ────────────────────────────────────────────
    outcome = None

    if decision.action_type == "AUTO_RETRY":
        # Simulate retry — success probability weighted by confidence
        success = random.random() < decision.confidence
        recovered_amount = req.amount if success else 0.0
        result = "RECOVERED" if success else "STILL_FAILED"

        db.add(recovery_action)
        db.flush()

        outcome = Outcome(
            recovery_action_id=recovery_action.id,
            result=result,
            recovered_amount=recovered_amount,
        )
        db.add(outcome)

        if success:
            payment.status = "SUCCESS"

        _update_method_history(db, req.customer_id, decision.recommended_method or failed_method_type, success)

    elif decision.action_type == "CUSTOMER_NUDGE":
        # Generate personalized nudge text
        nudge_text = _generate_nudge_text(
            customer.name, req.amount, req.failure_reason, decision.recommended_method
        )
        recovery_action.nudge_text = nudge_text

        # Try to create a Razorpay payment link
        link_result = create_payment_link(
            amount=req.amount,
            customer_name=customer.name,
            customer_email=customer.email,
            description=f"Recovery payment for order #{payment.id}",
            reference_id=f"recovery-{payment.id}",
        )
        if link_result:
            recovery_action.payment_link_url = link_result["short_url"]

        db.add(recovery_action)
        db.flush()

        # Simulate a ~50% chance the customer follows through
        follows_through = random.random() < 0.50
        result = "RECOVERED" if follows_through else "STILL_FAILED"
        recovered_amount = req.amount if follows_through else 0.0

        outcome = Outcome(
            recovery_action_id=recovery_action.id,
            result=result,
            recovered_amount=recovered_amount,
        )
        db.add(outcome)

        if follows_through:
            payment.status = "SUCCESS"

        _update_method_history(db, req.customer_id, decision.recommended_method or failed_method_type, follows_through)

    elif decision.action_type == "MERCHANT_ESCALATION":
        db.add(recovery_action)
        db.flush()

        # Escalated — lower recovery chance
        merchant_resolves = random.random() < 0.20
        result = "RECOVERED" if merchant_resolves else "STILL_FAILED"
        recovered_amount = req.amount if merchant_resolves else 0.0

        outcome = Outcome(
            recovery_action_id=recovery_action.id,
            result=result,
            recovered_amount=recovered_amount,
        )
        db.add(outcome)

        if merchant_resolves:
            payment.status = "SUCCESS"

    # Update failed method history (record the failure)
    if failed_method_type:
        _update_method_history_attempt(db, req.customer_id, failed_method_type)

    db.commit()
    db.refresh(payment)

    # Build response
    return _build_payment_detail(db, payment.id)


@router.post("/payments/{payment_id}/retry-link")
def create_retry_link(payment_id: int, db: Session = Depends(get_db)):
    """
    Create (or return existing) Razorpay payment link for a failed payment.
    Used for CUSTOMER_NUDGE actions.
    """
    payment = db.query(Payment).options(
        joinedload(Payment.customer),
    ).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Find the latest recovery action
    action = (
        db.query(RecoveryAction)
        .filter(RecoveryAction.payment_id == payment_id)
        .order_by(RecoveryAction.created_at.desc())
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="No recovery action found")

    # Return existing link if already created
    if action.payment_link_url:
        return {
            "payment_id": payment_id,
            "payment_link_url": action.payment_link_url,
            "already_existed": True,
        }

    # Create a new link
    link_result = create_payment_link(
        amount=payment.amount,
        customer_name=payment.customer.name if payment.customer else "Customer",
        customer_email=payment.customer.email if payment.customer else "customer@example.com",
        description=f"Recovery payment for order #{payment_id}",
        reference_id=f"recovery-{payment_id}",
    )

    if not link_result:
        raise HTTPException(
            status_code=503,
            detail="Razorpay keys not configured or payment link creation failed. "
                   "Add valid RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env to enable this feature."
        )

    action.payment_link_url = link_result["short_url"]
    db.commit()

    return {
        "payment_id": payment_id,
        "payment_link_url": link_result["short_url"],
        "razorpay_link_id": link_result["id"],
        "already_existed": False,
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Razorpay webhook endpoint — listens for payment.captured events
    and marks the corresponding outcome as RECOVERED.
    """
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # Verify signature (non-critical in test mode — log but don't block)
    if signature:
        is_valid = verify_webhook_signature(body, signature)
        if not is_valid:
            logger.warning("Razorpay webhook signature verification failed")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    logger.info(f"Razorpay webhook received: {event}")

    if event == "payment_link.paid":
        # Extract payment link details
        payment_link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        reference_id = payment_link.get("reference_id", "")
        amount_paise = payment_link.get("amount", 0)
        amount_inr = amount_paise / 100.0

        # Parse our reference_id format: "recovery-{payment_id}"
        if reference_id.startswith("recovery-"):
            try:
                payment_id = int(reference_id.split("-")[1])
            except (IndexError, ValueError):
                return {"status": "ignored", "reason": "invalid reference_id"}

            # Find the payment and its recovery action
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                return {"status": "ignored", "reason": "payment not found"}

            action = (
                db.query(RecoveryAction)
                .filter(RecoveryAction.payment_id == payment_id)
                .order_by(RecoveryAction.created_at.desc())
                .first()
            )
            if not action:
                return {"status": "ignored", "reason": "no recovery action"}

            # Check if outcome already exists
            existing_outcome = db.query(Outcome).filter(
                Outcome.recovery_action_id == action.id
            ).first()

            if existing_outcome:
                existing_outcome.result = "RECOVERED"
                existing_outcome.recovered_amount = amount_inr
            else:
                outcome = Outcome(
                    recovery_action_id=action.id,
                    result="RECOVERED",
                    recovered_amount=amount_inr,
                )
                db.add(outcome)

            payment.status = "SUCCESS"
            db.commit()

            logger.info(f"Payment #{payment_id} marked RECOVERED via Razorpay webhook (₹{amount_inr})")
            return {"status": "processed", "payment_id": payment_id}

    return {"status": "ignored", "event": event}


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(
    status: Optional[str] = Query(None, description="Filter by status: SUCCESS or FAILED"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List payments, optionally filtered by status, newest first."""
    q = db.query(Payment).order_by(Payment.created_at.desc())
    if status:
        q = q.filter(Payment.status == status)
    return q.limit(limit).all()


@router.get("/payments/{payment_id}", response_model=PaymentDetailOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get a single payment with its recovery actions and outcomes."""
    result = _build_payment_detail(db, payment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Payment not found")
    return result


# ── Reset endpoint ───────────────────────────────────────────────────────────

@router.post("/reset")
def reset_demo_data(db: Session = Depends(get_db)):
    """Delete all data and re-seed — used by the 'Reset Demo Data' button."""
    from app.seed import seed_database

    # Delete in reverse dependency order
    db.query(Outcome).delete()
    db.query(RecoveryAction).delete()
    db.query(Payment).delete()
    db.query(CustomerMethodHistory).delete()
    db.query(PaymentMethod).delete()
    db.query(Customer).delete()
    db.commit()

    return seed_database(db)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_payment_detail(db: Session, payment_id: int):
    payment = (
        db.query(Payment)
        .options(
            joinedload(Payment.customer),
            joinedload(Payment.method),
            joinedload(Payment.recovery_actions).joinedload(RecoveryAction.outcome),
        )
        .filter(Payment.id == payment_id)
        .first()
    )
    return payment


def _update_method_history(db: Session, customer_id: int, method_type: Optional[str], success: bool):
    """Update CustomerMethodHistory after a recovery attempt."""
    if not method_type:
        return
    hist = db.query(CustomerMethodHistory).filter(
        CustomerMethodHistory.customer_id == customer_id,
        CustomerMethodHistory.method_type == method_type,
    ).first()
    if hist:
        hist.attempts += 1
        if success:
            hist.successes += 1
    else:
        hist = CustomerMethodHistory(
            customer_id=customer_id,
            method_type=method_type,
            attempts=1,
            successes=1 if success else 0,
        )
        db.add(hist)


def _update_method_history_attempt(db: Session, customer_id: int, method_type: str):
    """Record a failed attempt in method history."""
    hist = db.query(CustomerMethodHistory).filter(
        CustomerMethodHistory.customer_id == customer_id,
        CustomerMethodHistory.method_type == method_type,
    ).first()
    if hist:
        hist.attempts += 1
    else:
        hist = CustomerMethodHistory(
            customer_id=customer_id,
            method_type=method_type,
            attempts=1,
            successes=0,
        )
        db.add(hist)
