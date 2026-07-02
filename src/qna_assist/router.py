from fastapi import APIRouter
from src.qna_assist.schema import QnaAssistRequest, QnaAssistResponse
from src.qna_assist import service

router = APIRouter(prefix="/admin/qna", tags=["qna-assist"])


@router.post("/{qna_id}/ai-summary", response_model=QnaAssistResponse)
async def ai_summary(qna_id: int, req: QnaAssistRequest):
    req.qna_id = qna_id
    return await service.summarize(req)
