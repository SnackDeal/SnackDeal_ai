import anthropic
from src.qna_assist.schema import QnaAssistRequest, QnaAssistResponse

client = anthropic.Anthropic()

SYSTEM_PROMPT = """
당신은 SnackDeal(과자 쇼핑몰) 고객센터 관리자 보조 AI입니다.
고객 문의 내용을 분석해서 다음 두 가지를 제공하세요:
1. 문의 핵심 요약 (2~3문장)
2. 답변 초안 (정중하고 명확하게, 관리자가 수정 후 사용)
"""


async def summarize(req: QnaAssistRequest) -> QnaAssistResponse:
    user_message = f"""
[문의 유형] {req.type}
[제목] {req.title}
[내용] {req.content}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text

    # TODO: 응답 파싱 로직 구체화 (요약 / 답변 초안 분리)
    return QnaAssistResponse(summary=raw, suggested_answer=raw)
