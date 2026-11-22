# Operating Debezium CDC Safely

운영 CDC는 소스 DB 변경을 읽는 경계다. 캡처 대상, 권한, 로그와 오프셋의 복구 조건, 다운스트림 계약을 함께 검토한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

## 1. 캡처 대상과 배포 변경을 통제한다

대상 스키마와 테이블을 목록으로 고정하고 전용 복제 계정을 둔다. 아웃박스 변환은 대상 이벤트에만 적용한다. DDL 전후로 스키마 이력과 이어 읽기, 소비자가 기존·신규 필드를 처리하는지 확인한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

## 2. 지연·오류·재해 복구를 구별한다

Connect REST에서 커넥터와 태스크 상태를 따로 본다. 소스 변경의 최신 시각, 업무 토픽 소비 지연, binlog 잔여 보존 시간을 함께 관측한다. 저장 위치와 스키마 이력을 지우기 전에 재처리할 범위와 다운스트림 상태 복구를 정한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)
