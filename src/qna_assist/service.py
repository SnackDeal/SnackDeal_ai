import os

from groq import Groq

from src.qna_assist.schema import QnaAssistRequest, QnaAssistResponse

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

SUMMARY_SYSTEM_PROMPT = """
당신은 SnackDeal(과자 쇼핑몰) 고객센터 관리자 보조 AI입니다.
고객 문의 내용을 2~3문장으로 핵심만 요약하세요.
제목, 마크다운 기호, 다른 설명 없이 요약 문장만 출력하세요.
"""

ANSWER_SYSTEM_PROMPT = """
당신은 SnackDeal(과자 쇼핑몰) 고객센터 관리자 보조 AI입니다.
고객 문의에 대한 답변 초안을 작성하세요. 관리자가 검토 후 그대로 고객에게 보낼 수 있도록,
정중하고 명확하게 작성하세요.
요약, 제목, 마크다운 기호 없이 답변 본문만 출력하세요.
"""


def _complete(system_prompt: str, user_message: str) -> str:
    client = Groq()
    completion = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return (completion.choices[0].message.content or "").strip()


async def summarize(req: QnaAssistRequest) -> QnaAssistResponse:
    user_message = f"""
[문의 유형] {req.type}
[제목] {req.title}
[내용] {req.content}
"""

    summary = _complete(SUMMARY_SYSTEM_PROMPT, user_message)
    answer = _complete(ANSWER_SYSTEM_PROMPT, user_message)
    return QnaAssistResponse(summary=summary, suggested_answer=answer)
