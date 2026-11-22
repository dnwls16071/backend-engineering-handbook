# Understanding Kafka for Saga Events

Kafka는 이벤트를 토픽의 파티션에 기록한다. 각 서비스는 자체 consumer group으로 필요한 이벤트를 읽으며, 읽은 위치는 오프셋으로 관리한다. [Apache Kafka 4.2 · Introduction](https://kafka.apache.org/42/getting-started/introduction/) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)

## 1. 키와 파티션이 제공하는 순서 범위를 확인한다

한 토픽 안에서 동일 주문의 이벤트를 같은 파티션으로 보내려면 주문 ID를 키로 사용하고 파티션 매핑이 유지되게 한다. 순서 보장은 파티션 로그 안에 적용된다. 여러 토픽이나 변경된 파티션 매핑에서 도착 순서를 전제로 삼지 않는다. [Apache Kafka 4.2 · Introduction](https://kafka.apache.org/42/getting-started/introduction/) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)

## 2. Kafka 내부의 보장과 DB 변경을 함께 설계한다

멱등 프로듀서는 구성 조건하에 프로듀서 재시도에 의한 로그 중복을 줄인다. Kafka 트랜잭션은 Kafka 출력과 Kafka 오프셋을 하나로 묶을 수 있다. 외부 DB 변경은 별도 경계이므로 이 예는 DB 로컬 트랜잭션에 멱등 기록을 둔다. [Apache Kafka 4.2 · Producer Configs](https://kafka.apache.org/42/configuration/producer-configs/) · [Apache Kafka 4.2 · Consumer Configs](https://kafka.apache.org/42/configuration/consumer-configs/) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
