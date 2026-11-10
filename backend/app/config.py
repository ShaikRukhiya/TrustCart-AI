import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./trustcart.db")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    paypal_client_id: str = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_client_secret: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
    paypal_base_url: str = os.getenv(
        "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
    ).rstrip("/")
    paypal_currency: str = os.getenv("PAYPAL_CURRENCY", "USD").upper()

    @property
    def paypal_configured(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)


settings = Settings()
