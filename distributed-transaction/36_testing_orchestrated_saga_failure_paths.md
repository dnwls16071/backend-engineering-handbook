# Testing Orchestrated Saga Failure Paths

실패 테스트는 HTTP 응답뿐 아니라 재고 수량, 포인트 원장, 주문 상태, 재개 기록을 함께 확인한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 실패 시점을 고정해 어떤 효과가 있어야 하는지 검증한다

| 주입 지점 | 기대 결과 | 근거 |
| --- | --- | --- |
| 재고 거절 | 포인트와 주문 생성 요청이 없고 재고 차감도 없다. | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |
| 재고 적용 뒤 포인트 거절 | 재고 복원은 한 번이며, 복원 완료 뒤 주문 취소가 보인다. | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) |
| 포인트 커밋 직후 응답 유실 | 결과 확인 또는 재시도 후 원장 차감은 한 건이다. | [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |
| 보상 전송 후 워커 재시작 | 같은 보상 키로 재개하며 잔액 증가가 중복되지 않는다. | [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |

## 2. 실패의 원인과 종료 조건을 노출한다

장애 해소 후 완료 조건을 기한이 있는 폴링으로 기다린다. 기한을 넘기면 마지막 단계 상태, 참가자 기록과 요청 키를 내보내 어떤 경계에서 멈췄는지 찾는다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
