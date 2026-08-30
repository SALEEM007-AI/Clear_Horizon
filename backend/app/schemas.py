"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Request Schemas ──────────────────────────────────────────────────────────

class PaymentSimulateRequest(BaseModel):
    customer_id: int
    amount: float = Field(gt=0)
    failure_reason: str = Field(
        default="INSUFFICIENT_FUNDS",
        description="One of: INSUFFICIENT_FUNDS, BANK_DOWN, OTP_TIMEOUT, CARD_DECLINED, NETWORK_ERROR",
    )
    method_id: Optional[int] = None


class OutcomeCreateRequest(BaseModel):
    result: str = Field(description="RECOVERED or STILL_FAILED")
    recovered_amount: float = Field(default=0.0, ge=0)


# ── Response Schemas ─────────────────────────────────────────────────────────

class PaymentMethodOut(BaseModel):
    id: int
    customer_id: int
    type: str
    last4: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class CustomerOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class CustomerWithMethodsOut(CustomerOut):
    payment_methods: List[PaymentMethodOut] = []


class MethodHistoryOut(BaseModel):
    id: int
    customer_id: int
    method_type: str
    attempts: int
    successes: int

    class Config:
        from_attributes = True


class RecoveryActionOut(BaseModel):
    id: int
    payment_id: int
    action_type: str
    confidence: float
    reasoning: Optional[str]
    recommended_method: Optional[str]
    payment_link_url: Optional[str] = None
    nudge_text: Optional[str] = None
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class OutcomeOut(BaseModel):
    id: int
    recovery_action_id: int
    result: str
    recovered_amount: float
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecoveryActionWithOutcomeOut(RecoveryActionOut):
    outcome: Optional[OutcomeOut] = None


class PaymentOut(BaseModel):
    id: int
    customer_id: int
    amount: float
    method_id: Optional[int]
    status: str
    failure_reason: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaymentDetailOut(PaymentOut):
    customer: Optional[CustomerOut] = None
    method: Optional[PaymentMethodOut] = None
    recovery_actions: List[RecoveryActionWithOutcomeOut] = []


class AgentDecision(BaseModel):
    action_type: str
    confidence: float
    recommended_method: Optional[str] = None
    reasoning: str


class MetricsOut(BaseModel):
    total_payments: int
    total_failed: int
    total_recovered: int
    total_still_failed: int
    total_recovered_amount: float
    agent_recovery_rate: float
    baseline_recovery_rate: float
    fees_saved: float
    recovery_actions_count: int


class CustomerHistoryOut(BaseModel):
    customer: CustomerOut
    payment_methods: List[PaymentMethodOut] = []
    method_history: List[MethodHistoryOut] = []
    recent_payments: List[PaymentOut] = []
