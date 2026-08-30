"""
SQLAlchemy ORM models — matches the data model from the implementation plan,
adapted to SQLite (no MySQL-specific types).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text,
)
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=_utcnow)

    # relationships
    payment_methods = relationship("PaymentMethod", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    method_history = relationship("CustomerMethodHistory", back_populates="customer")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    type = Column(String(50), nullable=False)       # CARD, UPI, NET_BANKING, WALLET
    last4 = Column(String(4), nullable=True)
    is_active = Column(Boolean, default=True)

    customer = relationship("Customer", back_populates="payment_methods")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    status = Column(String(20), nullable=False, default="FAILED")   # SUCCESS | FAILED
    failure_reason = Column(String(100), nullable=True)              # e.g. INSUFFICIENT_FUNDS
    created_at = Column(DateTime, default=_utcnow)

    customer = relationship("Customer", back_populates="payments")
    method = relationship("PaymentMethod")
    recovery_actions = relationship("RecoveryAction", back_populates="payment")


class CustomerMethodHistory(Base):
    """Tracks per-customer, per-method-type success history — powers the 'customer memory' feature."""
    __tablename__ = "customer_method_history"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    method_type = Column(String(50), nullable=False)
    attempts = Column(Integer, default=0)
    successes = Column(Integer, default=0)

    customer = relationship("Customer", back_populates="method_history")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    action_type = Column(String(30), nullable=False)    # AUTO_RETRY | CUSTOMER_NUDGE | MERCHANT_ESCALATION
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=True)
    recommended_method = Column(String(50), nullable=True)
    payment_link_url = Column(String(500), nullable=True)   # Razorpay payment link for CUSTOMER_NUDGE
    nudge_text = Column(Text, nullable=True)                # Personalized nudge message
    created_at = Column(DateTime, default=_utcnow)

    payment = relationship("Payment", back_populates="recovery_actions")
    outcome = relationship("Outcome", back_populates="recovery_action", uselist=False)


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, index=True)
    recovery_action_id = Column(Integer, ForeignKey("recovery_actions.id"), nullable=False)
    result = Column(String(20), nullable=False)    # RECOVERED | STILL_FAILED
    recovered_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)

    recovery_action = relationship("RecoveryAction", back_populates="outcome")
