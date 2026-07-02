from fastapi import FastAPI
from src.chatbot.router import router as chatbot_router
from src.qna_assist.router import router as qna_assist_router

app = FastAPI(title="SnackDeal AI Service")

app.include_router(chatbot_router)
app.include_router(qna_assist_router)


@app.get("/health")
def health():
    return {"status": "ok"}
