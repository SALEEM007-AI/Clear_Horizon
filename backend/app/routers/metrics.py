"""
Metrics router — outcome tracking and recovery metrics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Payment, RecoveryAction, Outcome
from app.schemas import MetricsOut, OutcomeCreateRequest, OutcomeOut

router = APIRouter(prefix="/api", tags=["metrics"])

# Simulated baseline: a flat retry-link strategy recovers ~40% of failures
BASELINE_RECOVERY_RATE = 0.40
# Assume ₹2 per retry attempt as gateway fee
GATEWAY_FEE_PER_RETRY = 2.0


@router.get("/metrics", response_model=MetricsOut)
def get_metrics(db: Session = Depends(get_db)):
    """
    Returns running totals: agent recovery rate vs. baseline,
    total recovered ₹, and fees saved from skipping low-confidence retries.
    """
    total_payments = db.query(func.count(Payment.id)).scalar() or 0
    total_failed = db.query(func.count(Payment.id)).filter(
        Payment.failure_reason.isnot(None)
    ).scalar() or 0

    # Count outcomes
    recovered_outcomes = (
        db.query(func.count(Outcome.id))
        .join(RecoveryAction, Outcome.recovery_action_id == RecoveryAction.id)
        .filter(Outcome.result == "RECOVERED")
        .scalar() or 0
    )

    still_failed_outcomes = (
        db.query(func.count(Outcome.id))
        .join(RecoveryAction, Outcome.recovery_action_id == RecoveryAction.id)
        .filter(Outcome.result == "STILL_FAILED")
        .scalar() or 0
    )

    total_recovered_amount = (
        db.query(func.sum(Outcome.recovered_amount))
        .filter(Outcome.result == "RECOVERED")
        .scalar() or 0.0
    )

    # Recovery actions count
    total_actions = db.query(func.count(RecoveryAction.id)).scalar() or 0

    # Agent recovery rate
    total_outcomes = recovered_outcomes + still_failed_outcomes
    agent_rate = (recovered_outcomes / total_outcomes * 100) if total_outcomes > 0 else 0.0

    # Baseline: flat 40% of all failed payments would be recovered
    baseline_rate = BASELINE_RECOVERY_RATE * 100

    # Fees saved: count of MERCHANT_ESCALATION actions (skipped retries) × fee
    escalations = (
        db.query(func.count(RecoveryAction.id))
        .filter(RecoveryAction.action_type == "MERCHANT_ESCALATION")
        .scalar() or 0
    )
    fees_saved = escalations * GATEWAY_FEE_PER_RETRY

    return MetricsOut(
        total_payments=total_payments,
        total_failed=total_failed,
        total_recovered=recovered_outcomes,
        total_still_failed=still_failed_outcomes,
        total_recovered_amount=round(total_recovered_amount, 2),
        agent_recovery_rate=round(agent_rate, 1),
        baseline_recovery_rate=round(baseline_rate, 1),
        fees_saved=round(fees_saved, 2),
        recovery_actions_count=total_actions,
    )


@router.post("/payments/{payment_id}/outcome", response_model=OutcomeOut)
def record_outcome(
    payment_id: int,
    req: OutcomeCreateRequest,
    db: Session = Depends(get_db),
):
    """Manually record an outcome for a payment's recovery action."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Find the latest recovery action for this payment
    action = (
        db.query(RecoveryAction)
        .filter(RecoveryAction.payment_id == payment_id)
        .order_by(RecoveryAction.created_at.desc())
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="No recovery action found for this payment")

    # Check if outcome already exists
    existing = db.query(Outcome).filter(Outcome.recovery_action_id == action.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Outcome already recorded")

    outcome = Outcome(
        recovery_action_id=action.id,
        result=req.result,
        recovered_amount=req.recovered_amount,
    )
    db.add(outcome)

    if req.result == "RECOVERED":
        payment.status = "SUCCESS"

    db.commit()
    db.refresh(outcome)
    return outcome
