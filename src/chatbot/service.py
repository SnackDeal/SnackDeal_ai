from __future__ import annotations

import logging
import os
from collections.abc import Callable
from functools import partial
from typing import Any, Protocol, TypedDict

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.chatbot.schema import ChatbotRequest, ChatbotResponse
from src.chatbot import faq_store

logger = logging.getLogger(__name__)

FALLBACK_ANSWER = "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
MISSING_API_KEY_ANSWER = "챗봇 API 키가 설정되지 않았습니다. 관리자에게 문의해 주세요."
RATE_LIMIT_ANSWER = "현재 챗봇 요청이 많습니다. 잠시 후 다시 시도해 주세요."
CONNECTION_ERROR_ANSWER = "챗봇 서버 연결이 불안정합니다. 잠시 후 다시 시도해 주세요."
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class ChatbotLlm(Protocol):
    async def generate(self, question: str, context: str) -> str:
        pass


class ChatbotGenerationError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class LlmClient:
    """Thin wrapper around the Groq client for chatbot answers."""

    SYSTEM_PROMPT = (
        "당신은 SnackDeal(과자 쇼핑몰) 고객센터 FAQ 챗봇입니다.\n"
        "제공된 FAQ 컨텍스트만 사용하여 답변하세요.\n"
        "FAQ 컨텍스트에 없는 정보는 추측하지 말고, 고객센터 또는 1:1 문의를 안내하세요.\n"
        "개인 주문, 배송, 결제, 환불, 회원 정보는 절대 만들어내지 마세요.\n"
        "한국어로 간결하고 친절하게 답변하세요.\n"
    )

    def __init__(self, groq_client: Groq | None = None) -> None:
        self._groq_client = groq_client
        self._groq_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    async def generate(self, question: str, context: str) -> str:
        if self._groq_client is None and not os.getenv("GROQ_API_KEY"):
            raise ChatbotGenerationError(MISSING_API_KEY_ANSWER)

        user_message = f"""[고객 질문]
{question}

[참고 가능한 고객센터 컨텍스트]
{context}
"""
        completion = self._request_completion(user_message)
        return completion.choices[0].message.content or ""

    def _request_completion(self, user_message: str):
        client = self._groq_client or Groq()
        try:
            return client.chat.completions.create(
                model=self._groq_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
        except RateLimitError as exc:
            raise ChatbotGenerationError(RATE_LIMIT_ANSWER) from exc
        except APIConnectionError as exc:
            raise ChatbotGenerationError(CONNECTION_ERROR_ANSWER) from exc
        except APIStatusError as exc:
            logger.warning("Groq API status error: status_code=%s", exc.status_code)
            raise ChatbotGenerationError(FALLBACK_ANSWER) from exc


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------


class QnaState(TypedDict, total=False):
    question: str
    context: str
    error: str
    answer: str
    personal_lookup: bool
    no_faq: bool


INPUT_VALIDATION_NODE = "validate_input"
CONTEXT_RETRIEVAL_NODE = "retrieve_context"
ANSWER_GENERATION_NODE = "generate_answer"
FALLBACK_NODE = "handle_fallback"


async def _validate_input(state: QnaState) -> dict[str, Any]:
    question = (state.get("question") or "").strip()
    if not question:
        return {"error": "질문이 비어 있습니다. 질문을 입력해 주세요."}
    return {"question": question}


async def _retrieve_context(state: QnaState) -> dict[str, Any]:
    question = state["question"]

    # 1. Check for personal lookup
    if faq_store.is_personal_lookup(question):
        return {
            "context": "",
            "personal_lookup": True,
            "no_faq": False,
        }

    # 2. Retrieve relevant FAQs
    faqs = faq_store.retrieve_relevant_faqs(question, limit=5)
    if not faqs:
        return {
            "context": "",
            "personal_lookup": False,
            "no_faq": True,
        }

    # 3. Build compact FAQ context
    context = faq_store.build_faq_context(faqs)
    return {
        "context": context,
        "personal_lookup": False,
        "no_faq": False,
    }


async def _generate_answer(
    state: QnaState,
    *,
    llm_provider: Callable[[], ChatbotLlm],
) -> dict[str, Any]:
    # Handle personal lookup without calling LLM
    if state.get("personal_lookup"):
        return {"answer": faq_store.PERSONAL_LOOKUP_ANSWER}

    # Handle no relevant FAQ found
    if state.get("no_faq"):
        return {"answer": faq_store.UNKNOWN_FALLBACK_ANSWER}

    try:
        answer = await llm_provider().generate(state["question"], state["context"])
    except ChatbotGenerationError as exc:
        logger.warning("Chatbot answer generation failed: %s", exc.user_message)
        return {"error": exc.user_message}
    except Exception:
        logger.exception("Unexpected chatbot answer generation failure")
        return {"error": FALLBACK_ANSWER}
    return {"answer": answer}


async def _handle_fallback(state: QnaState) -> dict[str, Any]:
    error = state.get("error", "알 수 없는 오류가 발생했습니다.")
    return {"answer": f"죄송합니다. {error}"}


def _route_after_validation(state: QnaState) -> str:
    return FALLBACK_NODE if state.get("error") else CONTEXT_RETRIEVAL_NODE


def _route_after_generation(state: QnaState) -> str:
    return FALLBACK_NODE if state.get("error") else END


def _build_graph(llm_provider: Callable[[], ChatbotLlm]) -> CompiledStateGraph:
    builder = StateGraph(QnaState)

    builder.add_node(INPUT_VALIDATION_NODE, _validate_input)
    builder.add_node(CONTEXT_RETRIEVAL_NODE, _retrieve_context)
    builder.add_node(ANSWER_GENERATION_NODE, partial(_generate_answer, llm_provider=llm_provider))
    builder.add_node(FALLBACK_NODE, _handle_fallback)

    builder.set_entry_point(INPUT_VALIDATION_NODE)
    builder.add_conditional_edges(INPUT_VALIDATION_NODE, _route_after_validation)
    builder.add_edge(CONTEXT_RETRIEVAL_NODE, ANSWER_GENERATION_NODE)
    builder.add_conditional_edges(ANSWER_GENERATION_NODE, _route_after_generation)
    builder.add_edge(FALLBACK_NODE, END)

    return builder.compile()


_graph: CompiledStateGraph | None = None
_llm: LlmClient | None = None


def _get_llm() -> LlmClient:
    global _llm
    if _llm is None:
        _llm = LlmClient()
    return _llm


def _get_graph() -> CompiledStateGraph:
    global _graph
    if _graph is None:
        _graph = _build_graph(_get_llm)
    return _graph


async def answer(req: ChatbotRequest) -> ChatbotResponse:
    graph = _get_graph()
    result = await graph.ainvoke({"question": req.message})
    return ChatbotResponse(answer=result.get("answer", ""))
