# Using CDC with Kafka and Debezium

Debezium MySQL 커넥터가 binlog의 커밋된 행 변경을 읽고 Kafka Connect가 Kafka로 전달한다. 변경 자체가 필요한지, 업무 이벤트가 필요한지에 따라 읽을 테이블을 고른다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 1. 행 변경 스트림과 업무 이벤트를 구분한다

검색 색인이나 조회 모델은 원본 행의 생성·변경·삭제를 반영할 수 있다. 주문 후속 업무는 주문 행의 모든 수정에서 시작하기보다 주문 접수와 함께 삽입한 아웃박스의 OrderRequested를 사용한다. 발행 스키마와 보존 규칙은 쓰기 모델에서 독립시킨다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 2. 게시와 소비의 복구 경계를 정한다

Connect 재시작 때 이미 전송한 변경이 다시 전달될 수 있다. 상태 복제는 원본 키와 순서를, 부수 효과는 발행한 고유 이벤트 ID를 기준으로 멱등하게 처리한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
