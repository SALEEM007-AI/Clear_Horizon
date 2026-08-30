"""
Razorpay integration — creates Payment Links for CUSTOMER_NUDGE recovery actions.
Uses Razorpay Test Mode so demo payments can be completed with test card numbers.
"""

import logging
from typing import Optional
import razorpay

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_client() -> Optional[razorpay.Client]:
    """
    Returns a configured Razorpay client, or None if keys are not set.
    """
    settings = get_settings()
    key_id = settings.razorpay_key_id
    key_secret = settings.razorpay_key_secret

    if (
        not key_id
        or not key_secret
        or key_id == "rzp_test_xxxxx"
        or key_secret == "xxxxx"
    ):
        logger.info("Razorpay keys not configured — skipping payment link creation.")
        return None

    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_link(
    amount: float,
    customer_name: str,
    customer_email: str,
    description: str,
    reference_id: str,
) -> Optional[dict]:
    """
    Create a Razorpay Payment Link (test mode).

    Args:
        amount: Amount in INR (will be converted to paise)
        customer_name: Customer's name
        customer_email: Customer's email
        description: Description for the payment link
        reference_id: Unique reference (e.g. "recovery-{payment_id}")

    Returns:
        dict with {short_url, id, amount, status} or None if creation fails
    """
    client = _get_client()
    if client is None:
        return None

    try:
        amount_paise = int(amount * 100)  # Razorpay uses paise

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": description,
            "reference_id": reference_id,
            "customer": {
                "name": customer_name,
                "email": customer_email,
            },
            "notify": {
                "email": False,  # Don't send emails in test mode
                "sms": False,
            },
            "callback_url": "http://localhost:5173/",
            "callback_method": "get",
        }

        result = client.payment_link.create(payload)

        logger.info(
            f"Created Razorpay payment link: {result.get('short_url')} "
            f"(id={result.get('id')}, amount={amount})"
        )

        return {
            "id": result.get("id"),
            "short_url": result.get("short_url"),
            "amount": amount,
            "status": result.get("status"),
        }

    except Exception as e:
        logger.warning(f"Failed to create Razorpay payment link: {e}")
        return None


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify that a webhook request actually came from Razorpay.
    """
    client = _get_client()
    if client is None:
        return False

    settings = get_settings()
    try:
        client.utility.verify_webhook_signature(
            payload.decode("utf-8"),
            signature,
            settings.razorpay_key_secret,
        )
        return True
    except Exception as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        return False
