from fastapi import APIRouter
from src.chatbot.schema import ChatbotRequest, ChatbotResponse
from src.chatbot import service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/ask", response_model=ChatbotResponse)
async def ask(req: ChatbotRequest):
    return await service.answer(req)
