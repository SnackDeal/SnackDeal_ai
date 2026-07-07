from fastapi import APIRouter
from src.chatbot.schema import ChatbotRequest, ChatbotResponse
from src.chatbot import service
from src.common.schema import CommonResponse

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/ask", response_model=CommonResponse[ChatbotResponse])
async def ask(req: ChatbotRequest) -> CommonResponse[ChatbotResponse]:
    response = await service.answer(req)
    return CommonResponse(
        success=True,
        code="SUCCESS",
        message="챗봇 응답 생성에 성공했습니다.",
        data=response,
    )
