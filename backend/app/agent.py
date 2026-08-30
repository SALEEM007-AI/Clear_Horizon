"""
Agent Decision Service — LLM-powered + rule-based fallback.

Takes payment failure context + customer method history, returns a structured
recovery decision: {action_type, confidence, recommended_method, reasoning}.
"""

import json
import logging
from typing import Optional

from app.config import get_settings
from app.schemas import AgentDecision

logger = logging.getLogger(__name__)

# ── Failure reasons the system recognises ────────────────────────────────────
FAILURE_REASONS = [
    "INSUFFICIENT_FUNDS",
    "BANK_DOWN",
    "OTP_TIMEOUT",
    "CARD_DECLINED",
    "NETWORK_ERROR",
]

METHOD_TYPES = ["CARD", "UPI", "NET_BANKING", "WALLET"]


# ── Rule-based fallback (deterministic, never breaks) ────────────────────────

def _best_alternative_method(
    failed_method_type: Optional[str],
    method_history: list[dict],
) -> str:
    """Pick the method with the highest success rate that isn't the one that just failed."""
    candidates = []
    for mh in method_history:
        if mh["method_type"] == failed_method_type:
            continue
        rate = mh["successes"] / max(mh["attempts"], 1)
        candidates.append((mh["method_type"], rate, mh["attempts"]))

    # Sort by success rate desc, then by attempts desc (prefer more data)
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

    if candidates and candidates[0][1] > 0:
        return candidates[0][0]

    # Default fallback order
    fallback_order = ["UPI", "CARD", "NET_BANKING", "WALLET"]
    for m in fallback_order:
        if m != failed_method_type:
            return m
    return "UPI"


def rule_based_decide(
    failure_reason: str,
    amount: float,
    failed_method_type: Optional[str],
    method_history: list[dict],
) -> AgentDecision:
    """
    Deterministic fallback — used when LLM is unavailable or API key is missing.
    Encodes the 3-tier confidence policy with simple heuristics.
    """
    alt_method = _best_alternative_method(failed_method_type, method_history)

    if failure_reason == "BANK_DOWN":
        return AgentDecision(
            action_type="AUTO_RETRY",
            confidence=0.85,
            recommended_method=alt_method,
            reasoning=(
                f"Bank is temporarily down. This is usually a transient issue. "
                f"Recommending automatic retry with {alt_method} which has "
                f"historically worked well for this customer. High confidence "
                f"because bank outages are typically short-lived."
            ),
        )

    if failure_reason == "OTP_TIMEOUT":
        # Check if customer has good UPI history
        upi_history = next(
            (mh for mh in method_history if mh["method_type"] == "UPI"), None
        )
        if upi_history and upi_history["successes"] > 0:
            return AgentDecision(
                action_type="AUTO_RETRY",
                confidence=0.78,
                recommended_method="UPI",
                reasoning=(
                    f"OTP timed out — likely a friction issue with card-based auth. "
                    f"This customer has {upi_history['successes']} successful UPI "
                    f"transactions. Recommending auto-retry via UPI to bypass OTP. "
                    f"High confidence based on customer's proven UPI track record."
                ),
            )
        return AgentDecision(
            action_type="CUSTOMER_NUDGE",
            confidence=0.55,
            recommended_method=alt_method,
            reasoning=(
                f"OTP timed out. Customer may have been distracted or had "
                f"connectivity issues during OTP entry. Sending a gentle nudge "
                f"suggesting they retry with {alt_method}. Medium confidence — "
                f"the customer needs to take action."
            ),
        )

    if failure_reason == "INSUFFICIENT_FUNDS":
        return AgentDecision(
            action_type="CUSTOMER_NUDGE",
            confidence=0.50,
            recommended_method=alt_method,
            reasoning=(
                f"Payment failed due to insufficient funds. Cannot auto-retry "
                f"the same method. Sending a personalised nudge to the customer "
                f"suggesting they use {alt_method} or add funds. Medium confidence "
                f"— depends on customer action."
            ),
        )

    if failure_reason == "CARD_DECLINED":
        return AgentDecision(
            action_type="MERCHANT_ESCALATION",
            confidence=0.30,
            recommended_method=None,
            reasoning=(
                f"Card was declined — this could indicate the card is blocked, "
                f"expired, or flagged by the issuing bank. Escalating to merchant "
                f"for review. Low confidence in automated recovery — the customer "
                f"may need to contact their bank directly."
            ),
        )

    if failure_reason == "NETWORK_ERROR":
        return AgentDecision(
            action_type="AUTO_RETRY",
            confidence=0.80,
            recommended_method=failed_method_type or alt_method,
            reasoning=(
                f"Network error during payment processing — a transient issue. "
                f"Recommending immediate retry with the same method. High confidence "
                f"as network errors are typically temporary."
            ),
        )

    # Unknown failure reason → escalate
    return AgentDecision(
        action_type="MERCHANT_ESCALATION",
        confidence=0.25,
        recommended_method=None,
        reasoning=(
            f"Unknown failure reason: '{failure_reason}'. Unable to determine "
            f"an appropriate automated recovery strategy. Escalating to merchant "
            f"for manual review. Low confidence."
        ),
    )


# ── LLM-powered decision (Anthropic Claude) ─────────────────────────────────

SYSTEM_PROMPT = """\
You are a Smart Failed-Payment Recovery Agent. Given a failed payment's context \
and the customer's payment method history, decide the best recovery action.

## Confidence-Tiered Policy
- **High confidence (≥ 0.75)**: AUTO_RETRY — automatically retry with a better \
payment method. Only recommend this when you are confident the retry will succeed.
- **Medium confidence (0.40 – 0.74)**: CUSTOMER_NUDGE — send a personalised \
message to the customer suggesting they retry with a specific method.
- **Low confidence (< 0.40)**: MERCHANT_ESCALATION — escalate to the merchant \
with a reasoning summary for manual review.

## Instructions
1. Analyse the failure_reason to understand WHY the payment failed.
2. Review the customer's method_history to find methods with good success rates.
3. Pick the action tier that matches your confidence level.
4. If recommending a retry, choose the best alternative method based on history.
5. Write clear, concise reasoning (2-3 sentences) explaining your decision.

## Response Format (strict JSON)
{
  "action_type": "AUTO_RETRY" | "CUSTOMER_NUDGE" | "MERCHANT_ESCALATION",
  "confidence": <float 0.0 to 1.0>,
  "recommended_method": "<METHOD_TYPE or null>",
  "reasoning": "<2-3 sentence explanation>"
}

Respond with ONLY the JSON object, no markdown formatting."""


async def llm_decide(
    failure_reason: str,
    amount: float,
    failed_method_type: Optional[str],
    method_history: list[dict],
) -> Optional[AgentDecision]:
    """
    Call Anthropic Claude to get a recovery decision.
    Returns None if the call fails (caller should use fallback).
    """
    settings = get_settings()

    if not settings.anthropic_api_key or settings.anthropic_api_key == "sk-ant-xxxxx":
        logger.info("No Anthropic API key configured — skipping LLM call.")
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        user_message = json.dumps(
            {
                "failure_reason": failure_reason,
                "amount": amount,
                "failed_method_type": failed_method_type,
                "customer_method_history": method_history,
            },
            indent=2,
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        data = json.loads(raw)

        return AgentDecision(
            action_type=data["action_type"],
            confidence=float(data["confidence"]),
            recommended_method=data.get("recommended_method"),
            reasoning=data["reasoning"],
        )

    except Exception as e:
        logger.warning(f"LLM call failed: {e}. Falling back to rules.")
        return None


# ── Public entry point ───────────────────────────────────────────────────────

async def decide(
    failure_reason: str,
    amount: float,
    failed_method_type: Optional[str],
    method_history: list[dict],
) -> AgentDecision:
    """
    Main decision function — tries LLM first, falls back to rules.
    """
    # Try LLM
    decision = await llm_decide(
        failure_reason, amount, failed_method_type, method_history
    )

    if decision is not None:
        logger.info(f"LLM decision: {decision.action_type} ({decision.confidence:.2f})")
        return decision

    # Fallback to deterministic rules
    decision = rule_based_decide(
        failure_reason, amount, failed_method_type, method_history
    )
    logger.info(f"Rule-based decision: {decision.action_type} ({decision.confidence:.2f})")
    return decision
