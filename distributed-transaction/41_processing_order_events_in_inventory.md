# Processing Order Events in Inventory

재고 서비스는 OrderRequested를 읽고, 동일 이벤트의 재처리 여부를 확인한 뒤 차감과 결과 이벤트 발행 의도를 기록한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)

## 1. DB 커밋이 끝난 뒤 오프셋을 진행한다

하나의 DB 트랜잭션에서 소비자 이름과 eventId의 처리 기록, 차감 또는 거절, StockDeducted 또는 StockRejected 아웃박스를 함께 저장한다. 커밋하고 난 뒤에 해당 메시지 처리를 Kafka에 반영한다. 파티션 안에서 병렬 처리한다면 완료되지 않은 앞선 오프셋을 건너뛰어 커밋하지 않는다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/) · [Apache Kafka 4.2 · Consumer Configs](https://kafka.apache.org/42/configuration/consumer-configs/)

## 2. 재전달에 대비해 업무 키도 유지한다

같은 eventId를 다시 받으면 이전 처리를 확인한다. 같은 차감 명령을 다른 eventId로 잘못 발행하는 경우에도 수량이 다시 줄지 않도록 주문과 작업 유형의 유니크 키로 업무 중복을 방어한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
