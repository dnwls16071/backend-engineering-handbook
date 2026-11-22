# Integrating Toss Payments and Preparing Checkout

테스트 상점에서 결제위젯과 서버 승인 경로를 연결한다. 클라이언트 키는 위젯에 전달하고, 시크릿 키는 서버의 비밀 저장소나 주입된 환경에서 읽는다. 클라이언트 키와 시크릿 키는 같은 테스트 상점과 연동 유형으로 준비한다. [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration) · [토스페이먼츠 API 인증과 멱등키](https://docs.tosspayments.com/reference/using-api/authorization)

## 1. 결제 요청 전에 주문과 기준 금액을 저장한다

가상 Checkout은 인증된 구매자가 보낸 상품 ID와 수량으로 서버에서 금액을 계산한다. 금액과 통화, 판매자 정보를 주문에 보존하고 별도 결제 시도를 만든다. 가격이나 할인 정책이 바뀌더라도 승인 검증에는 해당 시도에 연결된 주문의 기준 금액을 사용한다. [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration) · [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

| 모델 | 저장할 값 | 제약의 예 | 근거 |
| --- | --- | --- | --- |
| checkout_order | order_id, buyer_id, seller_id, expected_amount, currency, created_at | KRW 예제에서는 원 단위 정수와 양수 제약을 사용한다. | [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration) · [PostgreSQL 18 제약](https://www.postgresql.org/docs/18/ddl-constraints.html) |
| payment_attempt | attempt_id, order_id, pg_order_id, payment_key, approval_idempotency_key, state, version | pg_order_id와 승인 멱등 키는 같은 시도의 재전송에서 유지한다. 복수 상점이면 PG 식별자를 상점 단위로 구분한다. | [토스페이먼츠 승인 API](https://docs.tosspayments.com/reference) · [토스페이먼츠 API 인증과 멱등키](https://docs.tosspayments.com/reference/using-api/authorization) · [PostgreSQL 18 제약](https://www.postgresql.org/docs/18/ddl-constraints.html) |
| confirmed_payment | payment_id, order_id, attempt_id, payment_key, amount, currency, approved_at | payment_id는 내부 승인 ID이며 order_id를 고유하게 관리해 한 주문에 내부 승인 하나를 연결한다. | [토스페이먼츠 Payment 객체](https://docs.tosspayments.com/reference) · [PostgreSQL 18 제약](https://www.postgresql.org/docs/18/ddl-constraints.html) |

주문 ID는 서비스 내부 식별자다. 예시의 pg_order_id는 위젯과 PG로 전달하는 orderId이며 우리 결제 시도에 연결해 둔다. 미확인 시도가 있으면 결과 확인을 먼저 하고, 새로운 결제를 허용할 때 새 시도와 새 PG 주문번호를 발급한다. [토스페이먼츠 승인 API](https://docs.tosspayments.com/reference) · [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

시도 생성이 경합할 수 있으면 주문 행을 잠그고 미확인 시도가 있는지 확인한다. PostgreSQL에서는 CREATED·CONFIRMING·UNKNOWN 상태만 포함한 order_id 부분 유일 인덱스를 추가해 활성 시도를 한 건으로 제한할 수 있다. [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE) · [PostgreSQL 18 CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html) · [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 2. 결제위젯에서 인증 결과를 받는다

위젯을 초기화하고 서버에서 계산한 금액을 setAmount로 설정한다. 결제수단과 약관 영역을 렌더링한 뒤 PG 주문번호를 담아 requestPayment로 인증을 시작한다. 인증 성공 URL에서 paymentKey, orderId, amount를 받아 서버 승인 경로에 전달한다. 실패 URL은 오류 안내에 사용하며 서버는 실패 URL 도착 여부로 기존 시도의 확정 상태를 덮어쓰지 않는다. [토스페이먼츠 결제 흐름](https://docs.tosspayments.com/guides/v2/get-started/payment-flow) · [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration)

서버는 자기 주문을 승인할 권한이 있는지 확인하고, 주문번호와 금액을 저장한 시도와 대조한다. 승인 호출의 amount는 저장해 둔 기준 금액으로 구성한다. 불일치가 발생하면 해당 요청을 중단하고 주문·시도 식별자 기준으로 기록한다. [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration) · [토스페이먼츠 결제 연동 빠른 참조](https://docs.tosspayments.com/guides/v2/get-started/llms-quick-reference)

## 3. 결제 승인 요청을 서버에서 구성한다

카드 인증이 성공하면 서버가 인증 유효 시간 10분 안에 POST /v1/payments/confirm을 호출한다. Basic 인증에 사용하는 값은 시크릿 키 뒤에 콜론을 붙인 문자열을 Base64로 인코딩한 결과다. 아래는 필드 이름만 나타낸 요청 예시다. [토스페이먼츠 승인 API](https://docs.tosspayments.com/reference) · [토스페이먼츠 API 인증과 멱등키](https://docs.tosspayments.com/reference/using-api/authorization)

```http
POST /v1/payments/confirm
Authorization: Basic <encoded-secret-key-and-colon>
Idempotency-Key: <stable-key-for-this-attempt>
Content-Type: application/json

{
  "paymentKey": "<payment-key-from-authentication>",
  "orderId": "<saved-provider-order-id>",
  "amount": 10000
}
```

## 4. 테스트 환경에서 신뢰 경계를 확인한다

성공 URL만 직접 호출하는 경우, 다른 구매자의 주문번호를 제출하는 경우, 주문 금액을 바꾸는 경우를 검사한다. 정상 건은 PG 응답의 주문번호·결제 키·금액·통화까지 대조한 뒤 승인한다. [토스페이먼츠 결제위젯 v2](https://docs.tosspayments.com/guides/v2/payment-widget/integration) · [토스페이먼츠 Payment 객체](https://docs.tosspayments.com/reference)
