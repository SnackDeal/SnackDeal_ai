from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FAQ_DATA_PATH = Path(__file__).resolve().parent / "data" / "faq_seed.json"

# ---------- simple Korean keyword alias map ----------
_KEYWORD_ALIASES: dict[str, list[str]] = {
    "취소": ["주문취소"],
    "주문취소": ["취소"],
    "배송": ["배송조회", "운송장", "택배"],
    "배송조회": ["배송", "운송장", "택배"],
    "운송장": ["배송", "택배"],
    "택배": ["배송", "운송장"],
    "환불": ["반품"],
    "반품": ["환불"],
    "품절": ["재입고", "입고"],
    "재입고": ["품절", "입고"],
    "입고": ["품절", "재입고"],
    "이메일": ["인증", "코드"],
    "인증": ["이메일", "코드"],
    "코드": ["이메일", "인증"],
    "쿠폰": ["할인"],
    "할인": ["쿠폰"],
    "비밀번호": ["로그인"],
    "로그인": ["비밀번호"],
}

# Personal lookup keywords that should trigger the personal guidance path
_PERSONAL_KEYWORDS = [
    "내 주문",
    "내주문",
    "내 결제",
    "내결제",
    "내 배송",
    "내배송",
    "내 환불",
    "내환불",
    "내 계정",
    "내계정",
    "내 개인정보",
    "내개인정보",
]

# "주문번호" alone is a generic FAQ term; only treat it as a personal lookup
# when an actual order number follows (e.g. "주문번호 1234 배송 상태").
_PERSONAL_PATTERNS = [re.compile(r"주문번호\s*\d+")]

PERSONAL_LOOKUP_ANSWER = (
    "개인 주문/배송/결제 정보는 본인 확인이 필요해 챗봇에서 직접 확인할 수 없습니다. "
    "마이페이지 주문 상세에서 확인하시거나 고객센터 또는 1:1 문의를 이용해 주세요."
)

UNKNOWN_FALLBACK_ANSWER = (
    "해당 내용은 현재 FAQ에서 정확한 안내가 어렵습니다. " "정확한 확인을 위해 고객센터 또는 1:1 문의를 이용해 주세요."
)

# ---------- helpers ----------


def _normalize(text: str) -> str:
    """Lowercase, strip, remove simple punctuation except Korean-friendly chars."""
    text = text.lower().strip()
    # keep 한글, 영문, 숫자, 공백
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    # collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


# Trailing interrogative/filler suffixes that appear in almost every FAQ title
# (e.g. "확인하나요" -> "확인"). Longest suffixes first so they win over shorter ones.
_NOISE_SUFFIXES: tuple[str, ...] = (
    "그런가요", "가능한가요", "되나요", "하나요", "인가요", "있나요", "없나요",
    "않아요", "싶어요", "같아요",
)
_STANDALONE_STOPWORDS: set[str] = {"어디서", "어떻게", "무엇", "언제", "왜"}


def _clean_token(token: str) -> str | None:
    """Strip generic Korean interrogative suffixes; drop pure filler tokens."""
    for suffix in _NOISE_SUFFIXES:
        if token.endswith(suffix):
            stem = token[: -len(suffix)]
            return stem if len(stem) > 1 else None
    if token in _STANDALONE_STOPWORDS:
        return None
    return token


def _tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _normalize(text).split():
        if len(raw) <= 1:
            continue
        cleaned = _clean_token(raw)
        if cleaned:
            tokens.append(cleaned)
    return tokens


def _stem2(token: str) -> str:
    """Rough 2-char root used to bridge Korean particle/conjugation mismatches
    (e.g. question '취소는' vs FAQ content '취소하고' both stem to '취소')."""
    return token[:2]


# ---------- FAQ loading ----------


class FaqStore:
    """Lightweight in-memory FAQ store with simple keyword/token scoring."""

    def __init__(self) -> None:
        self._faqs: list[dict[str, str]] = []
        self._loaded = False

    def load(self, path: Path | None = None) -> None:
        path = path or _FAQ_DATA_PATH
        if not path.exists():
            logger.warning("FAQ data file not found: %s", path)
            self._faqs = []
            self._loaded = False
            return

        raw = json.loads(path.read_text(encoding="utf-8"))
        faqs: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            if not all(k in item for k in ("type", "title", "content")):
                logger.warning("Skipping FAQ item missing required fields: %s", item)
                continue
            faqs.append({"type": item["type"], "title": item["title"], "content": item["content"]})

        self._faqs = faqs
        self._loaded = True
        logger.info("Loaded %d FAQ items from %s", len(self._faqs), path)

    @property
    def faqs(self) -> list[dict[str, str]]:
        if not self._loaded:
            self.load()
        return self._faqs


# ---------- scoring ----------


def _score_faq(
    question_tokens: list[str],
    question_norm: str,
    faq: dict[str, str],
) -> float:
    """Score a single FAQ against the question.

    Scoring rules (simple additive):
    - token match in title:       2.0 per unique match
    - token match in content:     1.0 per unique match
    - token match in type:        0.5 per unique match
    - exact substring of question found in title:  +3.0
    - exact substring of question found in content: +1.5
    - alias expansion bonus: same weights applied for alias tokens
    """
    score = 0.0
    title_norm = _normalize(faq["title"])
    content_norm = _normalize(faq["content"])
    type_norm = _normalize(faq["type"])

    title_tokens = _tokenize(title_norm)
    content_tokens = _tokenize(content_norm)
    type_tokens = _tokenize(type_norm)

    # collect unique matched tokens (avoid double-counting)
    matched_title: set[str] = set()
    matched_content: set[str] = set()
    matched_type: set[str] = set()

    # include alias-expanded tokens
    all_question_tokens = list(question_tokens)
    for tok in question_tokens:
        for alias in _KEYWORD_ALIASES.get(tok, []):
            if alias not in all_question_tokens:
                all_question_tokens.append(alias)

    for token in all_question_tokens:
        if token in title_tokens and token not in matched_title:
            matched_title.add(token)
            score += 2.0
        if token in content_tokens and token not in matched_content:
            matched_content.add(token)
            score += 1.0
        if token in type_tokens and token not in matched_type:
            matched_type.add(token)
            score += 0.5

    # substring match bonus
    if len(question_norm) >= 3:
        if question_norm in title_norm:
            score += 3.0
        if question_norm in content_norm:
            score += 1.5

    # additional: if any question token appears as substring in title/content
    for token in question_tokens:
        if len(token) >= 2:
            if token in title_norm:
                score += 1.0
            if token in content_norm:
                score += 0.5

    # root-stem partial match: bridges Korean particle/conjugation mismatches
    # that exact-token matching misses (e.g. "취소는" vs "취소하고")
    title_stems = {_stem2(t) for t in title_tokens if len(t) >= 2}
    content_stems = {_stem2(t) for t in content_tokens if len(t) >= 2}
    for token in all_question_tokens:
        if len(token) < 2:
            continue
        stem = _stem2(token)
        if token not in matched_title and stem in title_stems:
            score += 1.0
        if token not in matched_content and stem in content_stems:
            score += 0.5

    return score


# ---------- singleton / public API ----------

_store: FaqStore | None = None


def _get_store() -> FaqStore:
    global _store
    if _store is None:
        _store = FaqStore()
        _store.load()
    return _store


def is_personal_lookup(question: str) -> bool:
    """Check whether the question is asking about personal order/delivery/payment/member info."""
    norm = _normalize(question)
    for kw in _PERSONAL_KEYWORDS:
        if kw in norm:
            return True
    for pat in _PERSONAL_PATTERNS:
        if pat.search(norm):
            return True
    return False


def retrieve_relevant_faqs(question: str, limit: int = 5, min_score: float = 1.5) -> list[dict[str, Any]]:
    """Return top-k relevant FAQ dicts for the given question.

    Returns [] when no FAQ exceeds *min_score*.
    """
    store = _get_store()
    if not store.faqs:
        return []

    question_norm = _normalize(question)
    tokens = _tokenize(question)
    if not tokens:
        return []

    scored: list[tuple[float, dict[str, str]]] = []
    for faq in store.faqs:
        s = _score_faq(tokens, question_norm, faq)
        if s >= min_score:
            scored.append((s, faq))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [faq for _, faq in scored[:limit]]


def build_faq_context(faqs: list[dict[str, str]]) -> str:
    """Build a compact context string from retrieved FAQ items."""
    if not faqs:
        return ""

    blocks: list[str] = []
    for i, faq in enumerate(faqs, start=1):
        blocks.append(
            f"[FAQ {i}]\n"
            f"분류: {faq['type']}\n"
            f"질문: {faq['title']}\n"
            f"답변: {faq['content']}"
        )
    return "\n\n".join(blocks)