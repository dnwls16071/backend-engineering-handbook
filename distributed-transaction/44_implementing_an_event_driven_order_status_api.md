# Implementing an Event-Driven Order Status API

주문 상태 조회 API는 주문 서비스가 소유한 상태를 조회한다. 신청 시 발급한 주문 ID로 대상과 마지막 진행 시각을 식별한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html)

## 1. 조회 상태와 실제 완료 조건을 연결한다

PENDING은 접수됐으나 최종 결과가 없는 상태다. 선택적으로 COMPENSATING을 표시한다. 여기서 CONFIRMED는 포인트 성공의 상태 반영, CANCELED는 재고 거절 또는 필요한 복원까지 완료한 상태로 정의한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 지연과 결과 미상을 노출한다

아직 주문 서비스에 결과 이벤트가 반영되지 않았으면 현재 상태와 갱신 시각을 제공한다. 오래된 진행 건은 트레이스나 이벤트 ID로 대사하되, 조회 API가 타임아웃만 보고 완료 결과를 임의로 바꾸지 않는다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)
