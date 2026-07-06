from __future__ import annotations

import logging
from collections.abc import Callable
from functools import partial
from typing import Any, Protocol, TypedDict

import anthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.chatbot.schema import ChatbotRequest, ChatbotResponse

logger = logging.getLogger(__name__)

CUSTOMER_CENTER_CONTEXT = """
SnackDeal 고객센터 기본 안내:
- 주문/결제: 주문 내역은 마이페이지 주문내역에서 확인할 수 있습니다.
- 배송: 배송지 등록/수정/기본 배송지 지정은 배송지 관리에서 처리합니다.
- 환불: 주문 상세에서 환불 요청을 진행하며, 결제/배송 상태에 따라 처리 방식이 달라질 수 있습니다.
- 쿠폰: 보유 쿠폰은 마이페이지 쿠폰함에서 확인하고, 이벤트 쿠폰은 이벤트 페이지에서 받을 수 있습니다.
- 상품: 상품 상세 페이지에서 가격, 재고, 상품 이미지를 확인할 수 있습니다.
- 문의: 정확한 주문번호나 개인정보가 필요한 건은 고객센터 문의 등록을 안내합니다.
""".strip()

FALLBACK_ANSWER = "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."


class ChatbotLlm(Protocol):
    async def generate(self, question: str, context: str) -> str:
        pass


class LlmClient:
    """Thin wrapper around the Anthropic client for chatbot answers."""

    SYSTEM_PROMPT = (
        "당신은 SnackDeal(과자 쇼핑몰) 고객센터 챗봇입니다.\n"
        "고객의 주문, 배송, 상품, 환불, 쿠폰 관련 질문에 친절하고 간결하게 답변하세요.\n"
        "모르는 내용은 솔직히 모른다고 하고 고객센터 문의를 안내하세요.\n"
    )

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    async def generate(self, question: str, context: str) -> str:
        user_message = f"""[고객 질문]
{question}

[참고 가능한 고객센터 컨텍스트]
{context}
"""
        message = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------


class QnaState(TypedDict, total=False):
    question: str
    context: str
    error: str
    answer: str


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
    topic_hints = []

    keyword_map = {
        "주문": ("주문", "주문 내역, 주문 상태, 주문번호 확인을 안내합니다."),
        "결제": ("결제", "결제 검증과 결제 완료 여부는 주문 단계와 연결됩니다."),
        "배송": ("배송", "배송지 관리와 배송 상태 확인 경로를 안내합니다."),
        "환불": ("환불", "환불 요청은 주문 상세에서 진행하도록 안내합니다."),
        "쿠폰": ("쿠폰", "쿠폰함과 이벤트 쿠폰 다운로드 경로를 안내합니다."),
        "상품": ("상품", "상품 상세 페이지에서 가격, 재고, 이미지 확인을 안내합니다."),
    }

    for keyword, (label, hint) in keyword_map.items():
        if keyword in question:
            topic_hints.append(f"- {label}: {hint}")

    topic_context = "\n".join(topic_hints) if topic_hints else "- 일반 문의: 고객센터 문의 등록을 안내합니다."
    return {"context": f"{CUSTOMER_CENTER_CONTEXT}\n\n질문 분류 힌트:\n{topic_context}"}


async def _generate_answer(
    state: QnaState,
    *,
    llm_provider: Callable[[], ChatbotLlm],
) -> dict[str, Any]:
    try:
        answer = await llm_provider().generate(state["question"], state["context"])
    except Exception:
        logger.warning("Chatbot answer generation failed")
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
