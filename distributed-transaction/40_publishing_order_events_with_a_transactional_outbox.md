# Publishing Order Events with a Transactional Outbox

주문을 접수한 로컬 트랜잭션에 PENDING 주문과 OrderRequested 발행 기록을 함께 저장한다. 릴레이가 발행 기록을 Kafka로 전달한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html)

## 1. 발행할 이벤트를 먼저 내구성 있게 저장한다

아웃박스에 eventId, sagaId 또는 orderId, 업무 타입, payload 버전, 필요한 상품·수량 정보를 저장한다. 한 주문을 함께 읽도록 파티션 키는 orderId를 사용한다. 브로커 확인 후 발행 기록을 처리 완료로 표시한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Apache Kafka 4.2 · Introduction](https://kafka.apache.org/42/getting-started/introduction/)

## 2. 발행 직후 프로세스가 종료되는 경우를 다룬다

브로커 수락 뒤 아웃박스 발행 표시가 실패하면 릴레이가 다시 보낼 수 있다. 발행 기록을 같은 eventId로 다시 사용하고, 소비자는 eventId로 중복을 걸러낸다. Kafka 프로듀서의 내장 멱등성을 별도 릴레이 실행의 중복 방지로 간주하지 않는다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Apache Kafka 4.2 · Producer Configs](https://kafka.apache.org/42/configuration/producer-configs/) · [Apache Kafka 4.2 · Design](https://kafka.apache.org/42/design/design/)
