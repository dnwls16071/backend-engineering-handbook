# Implementing an Orchestrated Order API

외부 주문 API는 접수와 상태 조회를 제공하고, 내부 워커가 재고·포인트·주문을 조정한다. 장시간 흐름은 접수에 대한 202 응답으로 표현할 수 있다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 1. 요청에서 상태 조회까지 연결한다

접수 트랜잭션에서 멱등 키와 PENDING 상태를 저장한다. 워커는 재고 차감, 포인트 차감, 주문 생성 순으로 진행한다. 명시적 실패가 나면 성공한 변경의 보상을 진행하고 보상이 끝난 뒤 취소를 확정한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 명확한 최종 상태를 응답한다

접수 응답에 상태 조회 URI를 포함한다. 결과가 미확인이거나 보상 중이면 그 상태를 그대로 조회할 수 있게 한다. 같은 키의 재접수는 해당 주문을 찾아 응답한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
