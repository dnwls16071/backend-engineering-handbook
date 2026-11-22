# Registering a MySQL Outbox Connector

MySQL·Kafka·Connect를 로컬 Compose로 실행한 뒤, 아웃박스만 읽는 Debezium 커넥터를 등록한다. Spring 앱은 변환된 workflow.orders 토픽을 읽는다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/)

## 1. 로컬 인프라의 연결 지점을 구성한다

아래를 compose.yaml로 저장한다. 예제는 단일 브로커와 로컬 전용 계정을 사용한다. Compose 서비스는 내부 주소, 호스트 앱은 127.0.0.1의 게시 포트를 사용한다. 아래의 세 포트를 이미 쓰고 있다면 앱과 명령의 주소도 함께 바꾼다. [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/) · [Docker Compose · Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Apache Kafka · Single-Broker Docker Compose](https://github.com/apache/kafka/blob/4.3.2/docker/examples/docker-compose-files/single-node/plaintext/docker-compose.yml)

```yaml
services:
  mysql-source:
    image: mysql:8.4
    command: ["--server-id=101", "--log-bin=mysql-bin", "--binlog-format=ROW", "--binlog-row-image=FULL"]
    environment:
      MYSQL_ROOT_PASSWORD: local-workflow-root
    ports: ["127.0.0.1:13306:3306"]
    volumes:
      - ./db-init.sql:/docker-entrypoint-initdb.d/10-workflow.sql:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "--silent"]
      interval: 3s
      timeout: 2s
      retries: 30
  kafka:
    image: apache/kafka:4.3.2
    ports: ["127.0.0.1:19092:19092"]
    environment:
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
      KAFKA_NODE_ID: "1"
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: INTERNAL://:29092,EXTERNAL://:19092,CONTROLLER://:29093
      KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka:29092,EXTERNAL://127.0.0.1:19092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "1"
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "1"
    healthcheck:
      test: ["CMD", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:29092", "--list"]
      interval: 5s
      timeout: 5s
      retries: 20
  connect-cdc:
    image: quay.io/debezium/connect:3.6
    depends_on:
      kafka: { condition: service_healthy }
      mysql-source: { condition: service_healthy }
    ports: ["127.0.0.1:18083:8083"]
    environment:
      BOOTSTRAP_SERVERS: kafka:29092
      GROUP_ID: workflow-connect
      CONFIG_STORAGE_TOPIC: workflow-connect-configs
      OFFSET_STORAGE_TOPIC: workflow-connect-offsets
      STATUS_STORAGE_TOPIC: workflow-connect-status
      CONFIG_STORAGE_REPLICATION_FACTOR: "1"
      OFFSET_STORAGE_REPLICATION_FACTOR: "1"
      STATUS_STORAGE_REPLICATION_FACTOR: "1"
```

## 2. 주문, 아웃박스, 처리 결과 스키마를 만든다

아래를 db-init.sql로 저장한다. MySQL 이미지가 빈 데이터 디렉터리를 초기화할 때 SQL을 실행한다. 아웃박스는 발행 대상 주문과 함께 쓰고 이후 갱신하지 않는다. CDC 계정은 로컬 실습용 복제 권한을 가지며, 앱 계정은 처리 결과 테이블에만 접근한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc) · [Docker Official Image · MySQL](https://hub.docker.com/_/mysql) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

```sql
CREATE DATABASE workflow_lab;
USE workflow_lab;

CREATE TABLE orders (
    id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    status VARCHAR(24) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE order_outbox (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    aggregatetype VARCHAR(64) NOT NULL,
    aggregateid VARCHAR(64) NOT NULL,
    type VARCHAR(64) NOT NULL,
    payload JSON NOT NULL
) ENGINE=InnoDB;

CREATE TABLE processed_order_events (
    event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE USER 'cdc'@'%' IDENTIFIED BY 'local-workflow-cdc';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT, LOCK TABLES ON *.* TO 'cdc'@'%';
CREATE USER 'workflow_app'@'%' IDENTIFIED BY 'local-workflow-app';
GRANT SELECT, INSERT, UPDATE ON workflow_lab.processed_order_events TO 'workflow_app'@'%';
```

## 3. 커넥터를 등록하고 변환된 토픽의 계약을 확인한다

아래를 workflow-connector.json으로 저장한다. 스키마 이력과 Connect 내부 토픽은 이 실습 프로젝트 안에서 독립적으로 사용한다. Event Router는 aggregatetype이 orders이면 workflow.orders로 보내고, aggregateid를 Kafka 키로 사용한다. JSON 본문 자체에 eventId를 둬 리스너가 이를 사용한다. [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc)

```json
{
  "connector.class": "io.debezium.connector.mysql.MySqlConnector",
  "tasks.max": "1",
  "database.hostname": "mysql-source",
  "database.port": "3306",
  "database.user": "cdc",
  "database.password": "local-workflow-cdc",
  "database.server.id": "184054",
  "topic.prefix": "workflow-cdc",
  "database.include.list": "workflow_lab",
  "table.include.list": "workflow_lab[.]order_outbox",
  "snapshot.mode": "initial",
  "include.schema.changes": "false",
  "tombstones.on.delete": "false",
  "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
  "schema.history.internal.kafka.topic": "workflow-schema-history",
  "key.converter": "org.apache.kafka.connect.storage.StringConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "false",
  "transforms": "outbox",
  "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
  "transforms.outbox.route.topic.replacement": "workflow.${routedByValue}",
  "transforms.outbox.table.expand.json.payload": "true"
}
```

```bash
docker compose up -d --wait
connect_url=http://127.0.0.1:18083
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins"
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic workflow-schema-history --partitions 1 --replication-factor 1 \
  --config cleanup.policy=delete --config retention.ms=-1 --config retention.bytes=-1
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic workflow.orders --partitions 3 --replication-factor 1
curl -fsS -o /dev/null -X PUT -H 'Content-Type: application/json' \
  --data-binary @workflow-connector.json "$connect_url/connectors/workflow-cdc/config"
curl -fsS --retry 15 --retry-all-errors --retry-delay 1 "$connect_url/connectors/workflow-cdc/status"
```

상태 API에서 커넥터·태스크가 RUNNING인지 확인한다. RUNNING은 초기 스냅샷 완료를 뜻하지 않으므로, 커넥터 로그 또는 스냅샷 메트릭에서 종료를 확인하고 이어서 주문을 넣는다. [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html)
