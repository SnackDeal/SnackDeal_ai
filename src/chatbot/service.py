import anthropic
from src.chatbot.schema import ChatbotRequest, ChatbotResponse

client = anthropic.Anthropic()

SYSTEM_PROMPT = """
당신은 SnackDeal(과자 쇼핑몰) 고객센터 챗봇입니다.
고객의 주문, 배송, 상품, 환불, 쿠폰 관련 질문에 친절하고 간결하게 답변하세요.
모르는 내용은 솔직히 모른다고 하고 고객센터 문의를 안내하세요.
"""


async def answer(req: ChatbotRequest) -> ChatbotResponse:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": req.message}],
    )
    return ChatbotResponse(answer=message.content[0].text)
