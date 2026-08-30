"""
Smart Failed-Payment Recovery Agent — FastAPI entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, Base, get_db
from app.routers import health, payments, customers, metrics
from app.seed import seed_database


# ── Lifespan: create tables on startup ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import models so Base.metadata knows about them
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield


# ── App factory ─────────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title="Smart Recovery Agent",
    description="AI-powered failed-payment recovery for Razorpay Buildathon Track 3",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS — allow the Vite dev server ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(payments.router)
app.include_router(customers.router)
app.include_router(metrics.router)


# ── Seed endpoint ───────────────────────────────────────────────────────────
@app.post("/api/seed", tags=["seed"])
def seed_data(db: Session = Depends(get_db)):
    """Seed the database with 10 demo customers and realistic history."""
    return seed_database(db)
