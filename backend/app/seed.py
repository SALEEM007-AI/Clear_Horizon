"""
Seed data — generates 10 demo customers with realistic payment method histories.
Patterns baked in:
  - Some customers where card fails but UPI works (classic pattern)
  - Some customers with mixed success across methods
  - Some customers with very little history (new users)
"""

import random
from sqlalchemy.orm import Session
from app.models import Customer, PaymentMethod, Payment, CustomerMethodHistory

DEMO_CUSTOMERS = [
    {"name": "Aarav Sharma", "email": "aarav.sharma@example.com"},
    {"name": "Priya Patel", "email": "priya.patel@example.com"},
    {"name": "Rahul Gupta", "email": "rahul.gupta@example.com"},
    {"name": "Sneha Reddy", "email": "sneha.reddy@example.com"},
    {"name": "Vikram Singh", "email": "vikram.singh@example.com"},
    {"name": "Ananya Iyer", "email": "ananya.iyer@example.com"},
    {"name": "Karan Mehta", "email": "karan.mehta@example.com"},
    {"name": "Deepa Nair", "email": "deepa.nair@example.com"},
    {"name": "Arjun Das", "email": "arjun.das@example.com"},
    {"name": "Meera Joshi", "email": "meera.joshi@example.com"},
]

# Method profiles per customer — (type, last4, is_active)
# and their history patterns — (method_type, attempts, successes)
CUSTOMER_PROFILES = [
    {
        # Card fails, UPI works — classic recovery pattern
        "methods": [("CARD", "4242", True), ("UPI", None, True)],
        "history": [
            {"method_type": "CARD", "attempts": 12, "successes": 3},
            {"method_type": "UPI", "attempts": 8, "successes": 7},
        ],
    },
    {
        # All methods work decently
        "methods": [("CARD", "1234", True), ("UPI", None, True), ("WALLET", None, True)],
        "history": [
            {"method_type": "CARD", "attempts": 10, "successes": 8},
            {"method_type": "UPI", "attempts": 5, "successes": 4},
            {"method_type": "WALLET", "attempts": 3, "successes": 3},
        ],
    },
    {
        # Prefers net banking, card sometimes fails
        "methods": [("CARD", "5678", True), ("NET_BANKING", None, True)],
        "history": [
            {"method_type": "CARD", "attempts": 7, "successes": 4},
            {"method_type": "NET_BANKING", "attempts": 15, "successes": 14},
        ],
    },
    {
        # New user, very little history
        "methods": [("CARD", "9012", True)],
        "history": [
            {"method_type": "CARD", "attempts": 2, "successes": 1},
        ],
    },
    {
        # UPI power user
        "methods": [("UPI", None, True), ("WALLET", None, True)],
        "history": [
            {"method_type": "UPI", "attempts": 20, "successes": 18},
            {"method_type": "WALLET", "attempts": 5, "successes": 4},
        ],
    },
    {
        # Card-only, moderate success
        "methods": [("CARD", "3456", True), ("CARD", "7890", False)],
        "history": [
            {"method_type": "CARD", "attempts": 8, "successes": 5},
        ],
    },
    {
        # Multiple methods, mixed results
        "methods": [("CARD", "2468", True), ("UPI", None, True), ("NET_BANKING", None, True)],
        "history": [
            {"method_type": "CARD", "attempts": 6, "successes": 2},
            {"method_type": "UPI", "attempts": 10, "successes": 9},
            {"method_type": "NET_BANKING", "attempts": 4, "successes": 3},
        ],
    },
    {
        # Wallet-heavy user
        "methods": [("WALLET", None, True), ("UPI", None, True)],
        "history": [
            {"method_type": "WALLET", "attempts": 12, "successes": 11},
            {"method_type": "UPI", "attempts": 3, "successes": 2},
        ],
    },
    {
        # Struggling user — lots of failures
        "methods": [("CARD", "1357", True), ("UPI", None, True), ("NET_BANKING", None, True)],
        "history": [
            {"method_type": "CARD", "attempts": 15, "successes": 4},
            {"method_type": "UPI", "attempts": 8, "successes": 3},
            {"method_type": "NET_BANKING", "attempts": 5, "successes": 2},
        ],
    },
    {
        # Net banking + UPI user
        "methods": [("NET_BANKING", None, True), ("UPI", None, True)],
        "history": [
            {"method_type": "NET_BANKING", "attempts": 10, "successes": 9},
            {"method_type": "UPI", "attempts": 7, "successes": 6},
        ],
    },
]

FAILURE_REASONS = ["INSUFFICIENT_FUNDS", "BANK_DOWN", "OTP_TIMEOUT", "CARD_DECLINED", "NETWORK_ERROR"]


def seed_database(db: Session) -> dict:
    """
    Seed the database with demo customers, payment methods, history,
    and a few sample failed payments. Returns a summary.
    """
    # Check if already seeded
    existing = db.query(Customer).count()
    if existing > 0:
        return {"message": f"Database already has {existing} customers. Skipping seed.", "seeded": False}

    created_customers = []

    for i, cust_data in enumerate(DEMO_CUSTOMERS):
        profile = CUSTOMER_PROFILES[i]

        # Create customer
        customer = Customer(name=cust_data["name"], email=cust_data["email"])
        db.add(customer)
        db.flush()  # Get the ID

        # Create payment methods
        for method_type, last4, is_active in profile["methods"]:
            pm = PaymentMethod(
                customer_id=customer.id,
                type=method_type,
                last4=last4,
                is_active=is_active,
            )
            db.add(pm)

        # Create method history
        for hist in profile["history"]:
            cmh = CustomerMethodHistory(
                customer_id=customer.id,
                method_type=hist["method_type"],
                attempts=hist["attempts"],
                successes=hist["successes"],
            )
            db.add(cmh)

        # Create a few sample past payments (mix of SUCCESS and FAILED)
        for _ in range(random.randint(2, 5)):
            status = random.choice(["SUCCESS", "SUCCESS", "FAILED"])
            payment = Payment(
                customer_id=customer.id,
                amount=round(random.uniform(100, 5000), 2),
                status=status,
                failure_reason=random.choice(FAILURE_REASONS) if status == "FAILED" else None,
            )
            db.add(payment)

        created_customers.append({"id": customer.id, "name": cust_data["name"]})

    db.commit()

    return {
        "message": f"Seeded {len(created_customers)} customers with methods, history, and sample payments.",
        "seeded": True,
        "customers": created_customers,
    }
