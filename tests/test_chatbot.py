from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from src.chatbot.schema import ChatbotRequest, ChatbotResponse
from src.main import app


class FakeGroqMessage:
    content = "배송은 보통 주문 후 순차적으로 진행됩니다. 자세한 상태는 마이페이지 주문내역에서 확인해 주세요."


class FakeGroqChoice:
    message = FakeGroqMessage()


class FakeGroqCompletion:
    choices = [FakeGroqChoice()]


class FakeGroqCompletions:
    def __init__(self) -> None:
        self.last_payload = None

    def create(self, **kwargs):
        self.last_payload = kwargs
        return FakeGroqCompletion()


class FakeGroqClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeGroqCompletions()


@pytest.fixture(autouse=True)
def reset_chatbot_graph():
    from src.chatbot import service as chatbot_service

    chatbot_service._graph = None
    chatbot_service._llm = None
    yield
    chatbot_service._graph = None
    chatbot_service._llm = None


@pytest.mark.asyncio
async def test_chatbot_service_generates_answer_with_groq(monkeypatch):
    """
    Given a valid customer question
    When the LangGraph chatbot pipeline generates an answer
    Then it should call Groq with the configured Llama 3.1 8B model.
    """
    # Given
    from src.chatbot import service as chatbot_service

    fake_client = FakeGroqClient()
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    chatbot_service._llm = chatbot_service.LlmClient(groq_client=fake_client)
    chatbot_service._graph = chatbot_service._build_graph(lambda: chatbot_service._llm)

    # When
    result = await chatbot_service.answer(ChatbotRequest(message="배송은 얼마나 걸리나요?"))

    # Then
    assert isinstance(result, ChatbotResponse)
    assert "마이페이지 주문내역" in result.answer
    payload = fake_client.chat.completions.last_payload
    assert payload["model"] == "llama-3.1-8b-instant"
    assert payload["messages"][0]["role"] == "system"
    assert "SnackDeal" in payload["messages"][0]["content"]
    assert "배송은 얼마나 걸리나요?" in payload["messages"][1]["content"]
    assert "배송" in payload["messages"][1]["content"]


def test_chatbot_ask_api_returns_common_response(monkeypatch):
    """
    Given a valid POST /chatbot/ask request
    When the API processes the question
    Then it should return the answer wrapped in CommonResponse format.
    """
    # Given
    from src.chatbot import service as chatbot_service

    fake_client = FakeGroqClient()
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    chatbot_service._llm = chatbot_service.LlmClient(groq_client=fake_client)
    chatbot_service._graph = chatbot_service._build_graph(lambda: chatbot_service._llm)
    client = TestClient(app)

    # When
    response = client.post("/chatbot/ask", json={"message": "쿠폰은 어디서 확인해?"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "SUCCESS"
    assert body["message"] == "챗봇 응답 생성에 성공했습니다."
    assert "answer" in body["data"]


def test_chatbot_ask_api_returns_400_for_blank_message():
    """
    Given a blank chatbot message
    When the API validates the request
    Then it should return a 400 CommonResponse error.
    """
    # Given
    client = TestClient(app)

    # When
    response = client.post("/chatbot/ask", json={"message": "   "})

    # Then
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "BAD_REQUEST"
    assert body["data"] is None


@pytest.mark.asyncio
async def test_chatbot_service_returns_fallback_when_groq_key_is_missing(monkeypatch):
    """
    Given no Groq API key is configured
    When the LangGraph chatbot pipeline tries to generate an answer
    Then it should return a user-facing setup fallback without calling Groq.
    """
    # Given
    from src.chatbot import service as chatbot_service

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    chatbot_service._llm = chatbot_service.LlmClient()
    chatbot_service._graph = chatbot_service._build_graph(lambda: chatbot_service._llm)

    # When
    result = await chatbot_service.answer(ChatbotRequest(message="배송 알려줘"))

    # Then
    assert isinstance(result, ChatbotResponse)
    assert "챗봇 API 키가 설정되지 않았습니다" in result.answer
