# Testing Kafka Saga Choreography

실습은 독립 Kafka와 참가자 DB에서 실제 이벤트를 발행하고 주문 상태와 각 서비스의 저장 결과를 확인하는 시나리오로 구성한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)

## 1. 재전달과 장애 복구의 기대 결과를 정의한다

| 시나리오 | 검증 결과 | 근거 |
| --- | --- | --- |
| 정상 주문 | 주문이 CONFIRMED가 되고 재고와 포인트가 각각 한 번 차감된다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) |
| 포인트 부족 | 재고가 원본 차감량만큼 한 번 복원된 뒤 주문이 CANCELED가 된다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) |
| 소비자의 DB 커밋 후 오프셋 반영 전 종료 | 메시지는 재전달될 수 있고, DB 수량과 원장 효과는 중복되지 않는다. | [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| 아웃박스 발행 후 완료 표시 전 종료 | 발행 레코드가 다시 전달돼도 종착 상태와 업무 결과를 유지한다. | [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |

## 2. 일시적 지연과 확정 실패를 구분한다

실행별 주문 키를 분리하고 기한이 있는 조회로 완료를 기다린다. 실패하면 마지막 주문 상태, 참가자 작업 상태와 부족한 이벤트를 남긴다. 지연 이벤트를 뒤늦게 전달해 종착 상태가 되돌아가지 않는지도 검증한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)
