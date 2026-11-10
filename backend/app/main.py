from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import agent, cart, orders, products
from app.seed import seed_products


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_products(db)
    yield


app = FastAPI(title="TrustCart AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        {
            settings.frontend_origin,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
    ),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ai_mode": "groq" if settings.groq_api_key else "fallback",
        "paypal_sandbox_configured": settings.paypal_configured,
    }


app.include_router(products.router)
app.include_router(cart.router)
app.include_router(agent.router)
app.include_router(orders.router)
