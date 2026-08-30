"""
Health-check router — confirms the backend is up and the DB is reachable.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Returns service status, database connectivity, and which optional
    integrations are configured (Razorpay, Anthropic).
    """
    settings = get_settings()

    # Check DB connectivity
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "smart-recovery-agent",
        "database": "connected" if db_ok else "unreachable",
        "integrations": {
            "razorpay": "configured" if settings.razorpay_key_id and settings.razorpay_key_id != "rzp_test_xxxxx" else "not_configured",
            "anthropic": "configured" if settings.anthropic_api_key and settings.anthropic_api_key != "sk-ant-xxxxx" else "not_configured",
        },
    }
