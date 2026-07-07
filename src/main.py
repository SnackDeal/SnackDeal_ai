from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.chatbot.router import router as chatbot_router
from src.qna_assist.router import router as qna_assist_router
from src.common.schema import CommonResponse

app = FastAPI(title="SnackDeal AI Service")

app.include_router(chatbot_router)
app.include_router(qna_assist_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    response = CommonResponse(
        success=False,
        code="BAD_REQUEST",
        message="요청값이 올바르지 않습니다.",
        data=None,
    )
    return JSONResponse(
        status_code=400,
        content=response.model_dump(),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
