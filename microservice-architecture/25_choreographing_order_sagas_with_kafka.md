# Choreographing Order Sagas with Kafka

Saga 코레오그래피에서는 각 서비스가 다른 서비스의 업무 이벤트를 관찰하고 자신의 로컬 상태를 전이한다. 주문 서비스는 고객에게 보여 줄 주문 상태를 소유하고, 재고와 포인트 서비스는 각자의 차감 및 보상 규칙을 소유한다. [AWS Prescriptive Guidance · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html)

## 1. 주문에서 재고·포인트 처리까지

| 발행 이벤트 | 소비 서비스 | 가능한 결과 |
| --- | --- | --- |
| `OrderPlaced` | 재고 | 재고 처리 후 `InventoryDeducted` 또는 `InventoryRejected` 발행 |
| `InventoryDeducted` | 포인트 | 포인트 처리 후 `PointsDebited` 또는 `PointsDebitRejected` 발행 |
| `PointsDebited` / `InventoryRejected` | 주문 | 각각 주문 확정 또는 취소 |
| `PointsDebitRejected` | 주문 | `COMPENSATING` 전이와 `OrderCompensationStarted` 발행 |
| `OrderCompensationStarted` | 재고 | 원래 차감 참조로 복원하고 `InventoryRestored` 발행 |
| `InventoryRestored` | 주문 | 보상 완료를 반영해 주문 취소 |

상태 조회 API는 접수 후 `PENDING`을 즉시 반환할 수 있다. 처리 완료 여부는 주문의 현재 상태에서 읽는다. 이벤트에는 `eventId`, `orderId`, `eventType`, 스키마 버전과 원인이 된 이벤트 ID를 담는다.

## 2. Kafka의 순서와 서비스의 멱등 처리

Kafka 토픽은 파티션으로 나뉘고, 주문 ID를 키로 사용하면 파티셔닝이 유지되는 같은 토픽에서 주문별 순서를 관리하기 쉽다. 여러 토픽을 가로지르는 전역 순서는 보장되지 않는다. 애플리케이션이 같은 파티션을 병렬 처리하면 그 안에서도 업무 반영 순서는 별도로 관리한다. 후속 단계가 선행 상태보다 먼저 관측되면 유효한 선행 상태가 생길 때까지 지연 처리하거나 복구 대상으로 기록한다. [Apache Kafka · Design](https://kafka.apache.org/43/design/design/)

1. 발행자는 업무 상태와 발행할 이벤트를 같은 DB 트랜잭션의 Outbox에 저장한다.
2. 소비자는 처리한 `eventId` 기록, 업무 변경, 후속 이벤트 Outbox를 같은 DB 트랜잭션에 반영한다. 이벤트 ID가 달라도 같은 차감이 재요청될 수 있으면 `(orderId, 단계)` 같은 업무 유일 키도 사용한다.
3. DB 커밋이 끝난 후 소비 오프셋을 갱신한다. 오프셋 갱신 전 중단되면 재전달될 수 있으므로 완료된 처리는 반복하지 않는다.

Kafka의 트랜잭션은 Kafka 안의 레코드와 오프셋을 함께 갱신할 수 있다. 외부 주문 DB의 커밋에는 별도 정합성 설계가 필요하다. [Apache Kafka · Message Delivery Semantics](https://kafka.apache.org/43/design/design/) · [AWS Prescriptive Guidance · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 테스트와 운영에서 확인할 흐름

정상 주문, 포인트 부족 뒤 재고 복원, 중복 발행, DB 커밋 뒤 소비자 재시작을 각각 검증한다. 토픽과 오프셋만 확인하면 실제 주문 완료를 알기 어렵다. 같은 `orderId`로 각 서비스의 이벤트와 상태를 연결하고, 오래된 `PENDING`·`COMPENSATING` 주문에서 마지막으로 기록한 단계와 후속 이벤트 발행 여부를 확인한다.

관련 문서 [Reliable Asynchronous Messaging Between Services](08_reliable_asynchronous_messaging_between_services.md) · [Designing Event-Driven Service Interactions](12_designing_event_driven_service_interactions.md)
