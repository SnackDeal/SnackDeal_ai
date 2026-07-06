"""
BDD-style tests for the QnA chatbot LangGraph service.

Tests are structured as Given / When / Then and use mocked LLM calls
so no real API key is required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.chatbot.schema import ChatbotRequest, ChatbotResponse


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Return an AsyncMock that stands in for LlmClient.generate()."""
    return AsyncMock()


@pytest.fixture
def service_with_mock_llm(mock_llm_client):
    """Patch the global graph so every test uses the supplied mock LLM."""
    from src.chatbot import service as chatbot_service
    from src.chatbot.service import _build_graph, _get_graph

    # Clear the module-level cache so a fresh graph is built.
    chatbot_service._graph = None
    chatbot_service._llm = None

    class MockLlmClient:
        async def generate(self, question: str, context: str) -> str:
            return await mock_llm_client(question, context)

    with patch.object(chatbot_service, "LlmClient", new=MockLlmClient):
        yield chatbot_service


# ============================================================================
# Test 1 – Successful chatbot answer generation
# ============================================================================


@pytest.mark.asyncio
async def test_chatbot_answer_success(service_with_mock_llm, mock_llm_client):
    """
    Given a valid user question
    When the chatbot service processes it through the LangGraph pipeline
    Then it should return a successful answer from the LLM.
    """
    # Given
    mock_llm_client.return_value = (
        "안녕하세요! SnackDeal 고객센터입니다. 무엇을 도와드릴까요?"
    )
    req = ChatbotRequest(message="배송은 얼마나 걸리나요?")

    # When
    result = await service_with_mock_llm.answer(req)

    # Then
    assert isinstance(result, ChatbotResponse)
    assert result.answer == "안녕하세요! SnackDeal 고객센터입니다. 무엇을 도와드릴까요?"
    mock_llm_client.assert_awaited_once()
    question, context = mock_llm_client.await_args.args
    assert question == "배송은 얼마나 걸리나요?"
    assert "배송" in context
    assert "SnackDeal 고객센터 기본 안내" in context


# ============================================================================
# Test 2 – Blank question validation failure
# ============================================================================


@pytest.mark.asyncio
async def test_blank_question_validation_failure(
    service_with_mock_llm, mock_llm_client
):
    """
    Given an empty question string
    When the chatbot service processes it
    Then it should return a fallback error answer without calling the LLM.
    """
    # Given
    req = ChatbotRequest(message="   ")

    # When
    result = await service_with_mock_llm.answer(req)

    # Then
    assert isinstance(result, ChatbotResponse)
    assert "질문이 비어 있습니다" in result.answer
    mock_llm_client.assert_not_called()


# ============================================================================
# Test 3 – LangGraph / LLM client failure fallback
# ============================================================================


@pytest.mark.asyncio
async def test_llm_failure_fallback(service_with_mock_llm, mock_llm_client):
    """
    Given the LLM client raises an exception
    When the chatbot service processes a valid question
    Then it should return a graceful fallback error answer.
    """
    # Given
    mock_llm_client.side_effect = RuntimeError("API unavailable")
    req = ChatbotRequest(message="환불은 어떻게 하나요?")

    # When
    result = await service_with_mock_llm.answer(req)

    # Then
    assert isinstance(result, ChatbotResponse)
    assert "답변 생성 중 오류가 발생했습니다" in result.answer
    mock_llm_client.assert_awaited_once()
    question, context = mock_llm_client.await_args.args
    assert question == "환불은 어떻게 하나요?"
    assert "환불" in context
