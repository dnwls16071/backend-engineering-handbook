# Implementing Idempotent Order Creation

주문 생성 단계는 재고와 포인트가 적용된 뒤 확정 주문을 저장한다. 시작할 때 만든 주문 ID를 재사용해 결과가 유실되어도 생성 여부를 확인한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 업무 주문과 진행 기록을 연결한다

예제에서 접수 시에는 workflow에 주문 ID와 원본 요청을 저장하고, 마지막 단계에서 같은 키의 orders 행을 만든다. 중복 요청은 원본과 동일할 때 기존 결과를 읽고 주문 본문이 다르면 충돌로 처리한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 2. 생성 결과를 확정한 후 보상 여부를 정한다

생성 응답이 끊겼다면 같은 키로 조회나 재시도부터 수행한다. 주문이 확정된 상태라면 재고나 포인트를 임의로 되돌리지 않고, 확정 이후 취소가 필요할 때 별도의 업무 계약을 적용한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
