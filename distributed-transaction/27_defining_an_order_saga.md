# Defining an Order Saga

실습의 성공 경로는 재고 차감, 포인트 차감, 주문 생성이다. 각 업무 변경은 해당 서비스의 로컬 트랜잭션에서 커밋한다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 1. 성공과 보상 명령을 짝짓는다

| 정방향 | 이미 커밋된 변경의 보상 | 근거 |
| --- | --- | --- |
| 재고 차감 | 원본 재고 차감의 수량만 복원한다. | [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |
| 포인트 차감 | 원본 차감을 참조해 포인트를 반환한다. | [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |
| 주문 생성 | 이 예에서는 최종 성공 단계다. 결과 미상이라면 같은 주문 ID로 생성 여부를 확인한다. | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |

## 2. 중간 상태를 사용자와 공유한다

재고 차감 후 포인트 결과 대기 중이면 주문은 진행 중이다. 취소가 결정돼도 보상이 완료되기까지 별도로 표시한다. 전체 주문 완료 사례와 나중에 들어오는 주문 취소 정책은 구분해 설계한다. [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted)
