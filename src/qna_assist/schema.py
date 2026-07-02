from pydantic import BaseModel


class QnaAssistRequest(BaseModel):
    qna_id: int
    title: str
    content: str
    type: str  # ORDER / SHIPPING / PRODUCT / OTHER


class QnaAssistResponse(BaseModel):
    summary: str
    suggested_answer: str
