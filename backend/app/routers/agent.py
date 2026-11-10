from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.cart import customer_id
from app.schemas import AgentResponse, ChatRequest
from app.services.agent_service import run_agent

router = APIRouter(prefix="/api/agent", tags=["AI shopping agent"])


@router.post("/chat", response_model=AgentResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    customer: str = Depends(customer_id),
):
    return run_agent(db, customer, request.message.strip())
