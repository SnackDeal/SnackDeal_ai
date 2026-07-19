# SnackDeal — AI Service

> 과자 쇼핑몰 풀스택 프로젝트의 AI 서비스 (챗봇 · 답변 추천)
> FastAPI · Python · Groq LLM · LangGraph

<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB" />
  <img src="https://img.shields.io/badge/FastAPI-009688" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C" />
  <img src="https://img.shields.io/badge/Groq-F55036" />
</p>

---

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [관련 리포지토리](#관련-리포지토리)
- [기능](#기능)
- [기술 스택](#기술-스택)
- [아키텍처](#아키텍처)
- [LangGraph 대화 흐름](#langgraph-대화-흐름)
- [환각 방지 설계](#환각-방지-설계)
- [API 명세](#api-명세)
- [폴더 구조](#폴더-구조)
- [학습 · 참고 데이터](#학습--참고-데이터)
- [구현 현황](#구현-현황)

---

## 프로젝트 소개

SnackDeal의 고객 응대를 돕는 별도 파이썬 서비스입니다.
Spring Boot 백엔드가 호출하는 내부 API 형태로 동작하며, 두 가지 기능을 제공합니다.

1. **AI 챗봇** — 사용자에게 직접 답변
2. **AI 답변 추천** — 담당자가 문의에 답변을 작성할 때 초안을 제안

> 두 기능의 차이 — 챗봇은 **사용자에게 직접** 답하고, 답변 추천은 **답변자를 보조**합니다.

## 관련 리포지토리

| 리포 | 설명 |
|---|---|
| [SnackDeal_backand](https://github.com/SnackDeal/SnackDeal_backand) | Spring Boot REST API · **프로젝트 전체 소개** |
| [SnackDeal_react](https://github.com/SnackDeal/SnackDeal_react) | React SPA (사용자 / 관리자) |
| [SnackDeal_ai](https://github.com/SnackDeal/SnackDeal_ai) | **현재 리포** · FastAPI AI 서비스 |

---

## 기능

### 1. AI 챗봇

주문 · 배송 · 상품 · 쿠폰 관련 질문에 실시간으로 답변합니다.
FAQ 데이터를 기반으로 답변을 구성하며, 개인 정보 조회가 필요한 질문은 답변하지 않고 안내로 대체합니다.


### 2. AI 답변 추천

질문게시판(QNA)에서 담당자가 답변을 작성할 때 동작합니다.

```
문의 등록 → 관리자가 답변 작성 페이지 진입 → AI가 문의 요약 + 답변 초안 생성
         → 담당자가 검토·수정 → 최종 등록
```

AI가 자동으로 등록하지 않고 반드시 사람이 검토하는 구조입니다.


---

## 기술 스택

| 구분 | 사용 기술 |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI · Uvicorn |
| LLM | Groq API |
| Orchestration | LangGraph |
| Data | AIHub 대화 데이터셋 (FAQ · 상담 시나리오) |
| Infra | Docker · Docker Compose |
| CI/CD | GitHub Actions → Docker 이미지 → AWS 배포 |

---

## 아키텍처

```
사용자
  │
React (챗봇 위젯)
  │
Spring Boot  ──POST /chatbot/ask──▶  FastAPI (AI 서비스)
                                        │
                                        ├─ LangGraph 대화 그래프
                                        ├─ FAQ 검색
                                        └─ Groq LLM 호출
```

- 프론트가 AI 서비스를 직접 호출하지 않고 **Spring Boot를 경유**합니다.
  인증 검증과 API 키 노출 방지를 백엔드에서 일괄 처리하기 위함입니다.
- AI 서비스는 Docker Compose 스택 안에서 내부 네트워크로만 노출됩니다.

---

## LangGraph 대화 흐름

단순 프롬프트 1회 호출 대신, 질문 유형 분기와 검증 단계를 그래프로 구성했습니다.

```
        [입력]
           │
   ┌───────▼────────┐
   │ 개인 조회성 판별 │   주문번호 · 내 주문 · 결제/배송 상태 등
   └───┬────────┬───┘
       │ Yes    │ No
       ▼        ▼
  [안내 응답]  [FAQ 검색]
  마이페이지·      │
  고객센터로    ┌──▼──┐
   유도        │ 매칭? │
              └─┬──┬─┘
           Yes  │  │  No
                ▼  ▼
        [Groq LLM 답변 생성]  [범위 밖 안내]
                │
                ▼
             [출력]
```

> 실제 노드/엣지 정의는 `app/graph/` 참고

---

## 환각 방지 설계

**문제** · 주문번호 · 배송 상태 같은 개인 조회 질문이 일반 FAQ와 매칭되어,
챗봇이 실제 정보를 아는 것처럼 답변할 위험이 있었습니다.

**원인** · FAQ 검색이 키워드 유사도 기반이라 "배송", "주문" 같은 단어만 보고
관련 없는 일반 FAQ를 가져올 수 있었습니다.

**해결**

- FAQ 검색 **이전**에 개인 조회성 질문을 먼저 감지하는 노드를 배치
  (주문번호 / 내 주문 / 결제 상태 / 배송 상태 등)
- 해당 질문은 FAQ 답변을 아예 생성하지 않고, 마이페이지 주문 상세 또는 고객센터 문의로 안내
- 시스템 프롬프트에서 답변 가능 범위를 명시적으로 제한

**결과** · 챗봇이 접근할 수 없는 개인 주문/배송 정보를 추측하지 않도록 답변 범위를 제한했습니다.

---

## API 명세

### `POST /chatbot/ask`

<table>
<tr><th>Request</th><th>Response</th></tr>
<tr><td>

```json
{
  "question": "배송은 언제오나요?",
  "session_id": "abc-123"
}
```

</td><td>

```json
{
  "answer": "배송은 주문 상태에 따라 달라집니다...",
  "type": "FAQ",
  "matched_faq_id": 12
}
```

</td></tr>
</table>

`type` 값: `FAQ` · `PERSONAL_REDIRECT`(개인 조회 안내) · `OUT_OF_SCOPE`

### `POST /qna/recommend`

<table>
<tr><th>Request</th><th>Response</th></tr>
<tr><td>

```json
{
  "title": "[기타] 쿠폰 적용이 안돼요",
  "content": "결제 시 쿠폰이 안 보입니다."
}
```

</td><td>

```json
{
  "summary": "쿠폰을 적용하는데 문제가 발생했습니다...",
  "draft": "고객님 안녕하세요. 쿠폰 적용 오류를..."
}
```

</td></tr>
</table>

> 엔드포인트 경로와 필드명은 실제 구현에 맞춰 수정하세요.

---

## 폴더 구조

```
app
├── main.py           FastAPI 엔트리포인트
├── api/              라우터 (chatbot · qna)
├── graph/            LangGraph 노드 · 엣지 정의
│   ├── nodes.py      개인조회 판별 · FAQ 검색 · 답변 생성
│   └── workflow.py   그래프 조립
├── services/         Groq 클라이언트 · FAQ 검색
├── data/             FAQ · 상담 시나리오 데이터
├── schemas/          요청/응답 모델
└── core/             설정 · 프롬프트
```

---

## 학습 · 참고 데이터

- **AIHub 대화 데이터셋** — 고객 상담 대화 패턴 및 응답 톤 참고
- **자체 FAQ 데이터** — 주문 · 배송 · 상품 · 쿠폰 · 기타 카테고리

> AIHub 데이터는 별도 이용 약관이 적용됩니다. 원본 데이터는 리포에 포함하지 않았습니다.

---


## 구현 현황

- [x] FastAPI 서비스 구성 · Spring Boot 연동
- [x] Groq LLM 호출
- [x] LangGraph 기반 대화 흐름
- [x] FAQ 검색 기반 답변
- [x] 개인 조회성 질문 감지 · 환각 방지
- [x] QNA 답변 추천 (요약 + 초안)
- [ ] 상품 · 주문 데이터 연동 응답 (현재는 FAQ 범위 내로 제한)
- [ ] 임베딩 기반 검색으로 전환 (현재 키워드 유사도)
- [ ] 대화 히스토리 기반 멀티턴 컨텍스트 강화
- [ ] 응답 품질 평가 지표 도입

---
