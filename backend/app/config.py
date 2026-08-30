"""
Configuration — loads .env and exposes typed settings via Pydantic.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── LLM Agent ──
    anthropic_api_key: str = ""

    # ── Razorpay Test Keys ──
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # ── Database ──
    database_url: str = "sqlite:///./recovery_agent.db"

    # ── Server ──
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
