# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 저장소의 정체

**코드 프로젝트가 아니라**, **SnackDeal(과자 쇼핑몰)** 의 **한글 제품 명세서를 Notion에서 내보낸 문서 모음**입니다 (학생 MVP). 빌드·린트·테스트·실행 단계가 없습니다. 여기서의 작업은 **Markdown 명세 문서를 읽고, DB 스키마와 일치하도록 수정**하는 것입니다.

문서는 두 종류입니다:

- **기능 명세**(화면·기능 단위). 본문 섹션: `선행조건` / `트리거` / `동작` / `예외 / 제한사항` / `비고`.
- **API 명세**(엔드포인트 단위). 본문 섹션: `Request`(Body/Query/Path 표 + JSON) / `Response`(상태코드 + JSON). 상단에 `개발순서`, `메서드`, `도메인`, `사용자/관리자`가 있습니다.

### 현재 폴더 구조 (도메인별로 재편됨)

원래 `기능정의서/`, `API 정의서/` 두 폴더로 나뉘어 있었으나, **도메인별 폴더 7개로 재편**했습니다. 각 폴더에 그 도메인의 기능 명세 + API 명세가 함께 있고, 맨 위 **`_개요.md`가 그 도메인 전체(DB 테이블·화면·API 목록)를 요약**합니다. 새 작업 시 해당 도메인의 `_개요.md`부터 읽으면 빠르게 파악됩니다.

- `1_회원_인증/` — member·이메일인증·로그인·회원정보·관리자 회원관리·마이페이지 메인
- `2_상품_카테고리/` — product/category (사용자 조회 + 관리자 상품/카테고리 관리)
- `3_장바구니/` — cart
- `4_주문_결제_배송/` — order·결제·주문내역·환불·주소록(delivery)·관리자 주문관리
- `5_쿠폰_이벤트/` — coupon·이벤트게시판(coupon_board)·쿠폰함·관리자 쿠폰관리
- `6_고객센터_문의/` — 공지·FAQ·문의(qna)·챗봇·관리자 QNA
- `7_관리자_공통/` — 관리자 로그인·대시보드

빈 `기능정의서/`(빈 템플릿 1개만 남음)·`API 정의서/`(비어 있음) 폴더와 루트의 `*.csv` 목차는 **재편 이전의 옛 구조**라 지금 파일 위치와 맞지 않습니다(참고용/삭제 대상). 재편으로 옮긴 `.md` 안의 문서 간 상대경로 링크는 깨진 상태이며, 대신 각 폴더의 `_개요.md`가 도메인 인덱스 역할을 합니다.

## 기준(Source of Truth): SQL 스키마

`C:\Users\Admin\Downloads\SnackDeal.sql`(ERDCloud 내보내기, 이 폴더 바깥에 있음)이 **최종 데이터 모델**입니다. 문서를 수정할 때 필드명·타입·enum 값은 **반드시 DDL과 일치**해야 합니다. 문서가 SQL과 충돌하면 **SQL이 우선**이고, 문서에 필요한데 SQL에 없는 것은 **지어내지 말고 표시(플래그)** 만 합니다.

### 문서가 따르는 규칙 (새 수정도 여기에 맞출 것)

- **모든 ID는 `BIGINT` 정수** — 예시에 `uuid`/문자열 쓰지 않음.
- **상품 옵션 없음**(옵션 테이블 없음), **상품 이미지 1장**(`product_image`에 상품당 1행, 응답은 `image_url`). 옵션·다중이미지 필드 되살리지 말 것.
- **member**: `birth`는 `DATE`, `gender`는 `MALE`/`FEMALE`, `phone`은 문자열; status `ACTIVE`/`INACTIVE`/`DELETED`. 닉네임/아바타 없음. 가입은 **이메일 인증**(`email_verification` 테이블: `code`, `verification_token`, `verified`).
- **product/category status**: `ACTIVE`/`INACTIVE`/`DELETED`; `deleted_at`으로 소프트 삭제.
- **coupon**: `issue_type` = `EVENT`/`SIGNIN`; `discount_type` = `FIXED`/`PERCENT`; `is_active` 플래그; **쿠폰 코드 입력 방식 없음**. `coupon_board_id`는 **nullable FK** — `EVENT`는 필수, `SIGNIN`은 null 허용.
- **coupon_board** = 이벤트게시판. 게시판 1개가 쿠폰 여러 개를 담음(1:N). 헷갈리기 쉬운 날짜 2개: **게시일 = `coupon_board.start_at`**(이벤트가 보이기 시작) vs **받기 오픈일 = `coupon.valid_from`**(다운로드가 열림). 관리자 순서: **게시판 먼저 등록 → 그 게시판을 선택해 쿠폰 등록**.
- **user_coupon.status**: `ACTIVE`/`USED`/`EXPIRED`.
- **orders.status**: `PENDING_PAYMENT`/`PAYMENT_COMPLETED`/`PREPARING_SHIPMENT`/`SHIPPED`/`COMPLETED`/`CANCELLED`/`REFUND_REQUESTED`/`REFUND_COMPLETED`. 금액 필드: `product_amount`/`shipping_fee`/`discount_amount`/`final_amount`. 쿠폰은 `user_coupon_id`로 참조.
- **주문은 3개 테이블로 분리**: `orders`, `shipping`(주문별 스냅샷: `zipcode`/`address`/`detail_address`/`delivery_request`/`courier`/`tracking_number`, status `READY`/`PREPARING`/`SHIPPING`/`DELIVERED`), `payment`(`imp_uid`/`merchant_uid`/`pg_provider`=`tosspayments`, status `READY`/`PAID`/`FAILED`/`CANCELLED`).
- **delivery** = 재사용 가능한 **주소록**(배송지, `is_default` 포함). `member` 및 주문별 `shipping` 스냅샷과 별개.
- **qna/faq.type**: `ORDER`/`SHIPPING`/`PRODUCT`/`OTHER`; `qna.is_answered`는 불리언(상태 enum 아님); `qna_answer`는 qna당 1건(UNIQUE).
- **결제**는 **포트원 SDK → 토스페이먼츠 테스트 모드**(`prepare` → SDK 결제 → `complete` 서버 재검증).

## 도메인별 구성 (기능 문서 + API)

도메인은 `user/*`(사용자)와 `admin/*`(관리자)로 나뉩니다. `★`는 이번 세션에 새로 만든 문서(CSV 목차 미반영).

### 사용자 (user)

- **member (회원/인증)** — 기능: 회원가입 · 이메일인증 · 로그인 · 회원정보 관리
  - `POST /member/join`, `POST /member/email/send-code`, `POST /member/email/verify-code`, `POST /member/login`, `POST /member/logout`, `POST /member/token/refresh`, `GET /member/me`, `PATCH /member/me`
- **product (상품)** — 기능: 상품리스트페이지 · 상품 상세 페이지
  - `GET /product/list`, `GET /product/{product_id}`
- **cart (장바구니)** — 기능: 장바구니
  - `GET /cart`, `POST /cart`, `PATCH /cart/{item_id}`, `DELETE /cart`
- **order (주문/결제)** — 기능: 주문정보입력 페이지(결제) · 주문내역 조회
  - `POST /order/prepare`, `POST /order/complete`, `GET /order/list`, `GET /order/{order_id}`, `POST /order/{order_id}/refund`
- **delivery (주소록)** — 기능: 주소록(배송지 관리) ★
  - `GET /delivery`, `POST /delivery`, `PUT /delivery/{id}`, `PATCH /delivery/{id}/default`, `DELETE /delivery/{id}` ★ (한 파일에 정리)
- **coupon / event (쿠폰·이벤트)** — 기능: 이벤트페이지(쿠폰 다운로드) · 쿠폰함
  - `GET /event/coupon/list`, `POST /event/coupon/{coupon_id}/download`, `GET /mypage/coupon`
- **cs (고객센터)** — 기능: 공지사항게시판 · 문의하기 · 고객센터 챗봇페이지
  - `GET /cs/notice/list`, `GET /cs/notice/{id}`, `GET /cs/qna/faq`, `GET /cs/qna/list`, `GET /cs/qna/{id}`, `POST /cs/qna` ★, `PATCH /cs/qna/{id}`, `DELETE /cs/qna/{id}`, `POST /chatbot/ask`
- **mypage** — 기능: 마이페이지 메인(자체 API 없음, 주문내역·쿠폰함·주소록으로 진입)

### 관리자 (admin)

- **admin (로그인/대시보드)** — 기능: 관리자_로그인 · 관리자_대시보드
  - `POST /admin/login`, `GET /admin/main`
- **admin/product (상품관리)** — 기능: 관리자_상품관리 리스트 · 관리자_상품 등록/수정
  - `GET /admin/product`, `POST /admin/product`, `GET /admin/product/{id}`, `PUT /admin/product/{id}`, `PATCH /admin/product/{id}/status`
- **admin/category (분류관리)** — 기능: 관리자_카테고리 페이지
  - `GET /admin/category`, `POST /admin/category`, `PUT /admin/category/{id}`, `DELETE /admin/category/{id}`(비활성=deleted_at)
- **admin/order (주문관리)** — 기능: 관리자_주문관리
  - `GET /admin/order`, `GET /admin/order/{id}`, `PATCH /admin/order/{id}/status`, `POST /admin/order/{id}/refund`
- **admin/coupon (쿠폰관리)** — 기능: 관리자_쿠폰관리페이지
  - `GET /admin/coupon`, `POST /admin/coupon`, `PUT /admin/coupon/{id}`, `PATCH /admin/coupon/{id}/status`
  - 이벤트게시판 CRUD `GET/POST/PUT/DELETE /admin/coupon-board` ★ (한 파일에 정리)
- **admin/users (회원관리)** — 기능: 관리자_회원 관리
  - `GET /admin/members`, `GET /admin/members/{id}`, `PATCH /admin/members/{id}/status`
- **admin/qna (문의관리)** — 기능: 관리자_QNA관리
  - `GET /admin/qna`, `GET /admin/qna/{id}`, `POST /admin/qna/{id}/answer`

> 미확정 갭: 공지(notice)는 사용자 조회 API만 있고 **관리자 공지 CRUD API가 없음**. 환불 요청 상태 관리(REFUND_REQUESTED)는 별도 이력/플래그 처리 방식이 팀 확인 대기.

## Notion 내보내기 파일 규칙 (중요 주의점)

- 파일명은 `<한글 제목> <32자리 hex-id>.md` 형식이며, 끝의 hex는 Notion 페이지 ID라 **항상 맨 뒤에 있어야** 합니다. 각 파일 첫 줄은 `# <제목>` H1.
- 문서 간 링크는 파일명을 그대로 담은 **상대경로 URL 인코딩** 경로입니다. **파일 이름을 바꾸면 그 파일을 가리키던 모든 링크가 깨집니다.** 이름을 바꾸면 참조하는 쪽도 고치거나, 링크가 깨진다는 사실을 명시할 것.
- **파일 추가·이름 변경은 CSV 목차에 자동 반영되지 않습니다.** 새 문서(예: `admin coupon-board.md`, `cs qna create.md`, `delivery` API)는 수동으로 추가하지 않는 한 `*.csv`에 안 나오고, Notion 재가져오기로도 자동 인식되지 않습니다.
- 빈 `제목 없음 <id>.md` 파일은 Notion 자리표시 페이지이며, 새 문서로 재활용 가능합니다.
- 수정·추가된 기능 문서는 파일명에 `[수정됨]` / `[신규]` 접두어와 H1에 `(수정됨)` / `(신규)` 접미어가 붙어 있을 수 있습니다 — 검토 추적용 표시이지 제목의 일부가 아닙니다. 요청 시 제거.

## 연관 자산 (이 폴더 바깥)

`C:\Users\Admin\Downloads\` 에 HTML **UI 목업**이 있습니다 (`admin_coupon_management_mockup.html`, `admin_coupon_edit_v2_mockup.html`, `admin_coupon_board_list_mockup.html`, `admin_coupon_board_edit_mockup.html`). CSS 커스텀 속성(`var(--surface-1)`, `var(--text-accent)` …)으로 스타일링되어 있습니다. 쿠폰/게시판 명세 변경 시 함께 맞춰야 합니다.

## 수정 작업 방식

- 각 문서의 기존 섹션 구조와 한글 어조를 유지하며 **최소 범위로** 수정합니다.
- 스키마 기준 수정 후에는 `**/*.md` 전체에서 낡은 값(옛 `uuid`, 소문자 enum, 제거된 개념인 옵션·코드쿠폰 등)을 grep으로 훑어 잔재를 잡습니다.
- 문서에 필요한데 스키마에 정말 없으면, 표/컬럼을 지어내지 말고 **팀 확인용 인라인 표시**를 남깁니다.
