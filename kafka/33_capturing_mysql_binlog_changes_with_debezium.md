# Capturing MySQL Binlog Changes with Debezium

Debezium MySQL 커넥터는 커밋된 행 변경을 MySQL binlog에서 읽어 Kafka로 보낸다. 이 실습에서는 MySQL 8.4와 Debezium 3.7을 사용해 `shop.orders`의 스냅샷, INSERT, UPDATE, DELETE를 같은 토픽에서 확인한다. [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Debezium 3.7 · Tested Versions](https://debezium.io/releases/3.7/)

## 1. 테이블 폴링과 로그 기반 CDC

| 방식 | 읽는 대상 | 고려할 점 |
| --- | --- | --- |
| 테이블 폴링 | 주기적으로 `updated_at`이나 증가하는 ID를 조건으로 `SELECT`한다. | 조회 사이에 여러 번 바뀐 행은 마지막 상태만 보일 수 있다. 물리 삭제는 삭제 플래그나 별도 로그 테이블로 기록해야 한다. 조회 주기, 인덱스, 동일 타임스탬프 경계도 관리한다. |
| 로그 기반 CDC | MySQL이 복제를 위해 기록한 binlog를 순서대로 읽는다. | 조회 사이에 발생한 변경도 개별 이벤트로 포착하고 삭제와 변경 전후 값을 읽는다. 초기 데이터 조회, 복제 권한, binlog 보관 기간, 재시작 위치를 관리한다. |

Debezium은 기본적으로 테이블별 토픽을 사용한다. `topic.prefix=mysql-cdc`이면 `shop.orders`의 행 변경은 `mysql-cdc.shop.orders`에 기록된다. 같은 키의 순서는 같은 파티션에서 유지된다. 여러 테이블의 트랜잭션 경계를 소비자가 알아야 한다면 트랜잭션 메타데이터와 소비 방식을 별도로 설계한다. [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Apache Kafka · Guarantees](https://kafka.apache.org/43/getting-started/introduction/)

## 2. MySQL 복제 설정과 Connect 플러그인

[01번 Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)의 `compose.yaml` 옆에 아래를 `compose.mysql-cdc.yaml`로 저장한다. MySQL의 `server_id=101`과 Connect 설정의 `database.server.id=184054`는 다른 복제 참여자를 구분한다. `ROW`는 행 변경을, `FULL`은 변경 전후 이미지에 모든 컬럼을 기록한다. [MySQL 8.4 · Binary Logging Options](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html)

```yaml
services:
  mysql-source:
    image: mysql:8.4
    command:
      - --server-id=101
      - --log-bin=mysql-bin
      - --binlog-format=ROW
      - --binlog-row-image=FULL
      - --default-time-zone=+00:00
    environment:
      MYSQL_ROOT_PASSWORD: local-mysql-root
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "--silent"]
      interval: 2s
      timeout: 3s
      retries: 30
  connect-cdc:
    image: quay.io/debezium/connect:3.7
    depends_on:
      kafka: { condition: service_healthy }
      mysql-source: { condition: service_healthy }
    ports: ["127.0.0.1:18083:8083"]
    environment:
      BOOTSTRAP_SERVERS: kafka:29092
      GROUP_ID: mysql-cdc-connect
      CONFIG_STORAGE_TOPIC: mysql-cdc-connect-configs
      OFFSET_STORAGE_TOPIC: mysql-cdc-connect-offsets
      STATUS_STORAGE_TOPIC: mysql-cdc-connect-status
      CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR: "1"
      CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR: "1"
      CONNECT_STATUS_STORAGE_REPLICATION_FACTOR: "1"
      CONNECT_KEY_CONVERTER_SCHEMAS_ENABLE: "true"
      CONNECT_VALUE_CONVERTER_SCHEMAS_ENABLE: "true"
```

Debezium 이미지에는 MySQL 커넥터가 포함돼 있다. 기존 Connect 워커에 설치할 때는 MySQL 플러그인 배포 파일을 별도 디렉터리에 풀고 그 상위 디렉터리를 각 워커의 `plugin.path`에 추가한 뒤 워커를 다시 시작한다. 두 경우 모두 `GET /connector-plugins`에서 클래스를 확인한다. 08번 Connect 실습도 호스트 포트 `18083`을 사용하므로 이 실습에 앞서 해당 워커를 중지한다. [Debezium · Installing Kafka Connect Connectors](https://debezium.io/documentation/reference/3.7/install-kafka-connect.html) · [Debezium · Connect Tutorial](https://debezium.io/documentation/reference/3.7/tutorial.html) · [Kafka Connect 워커 실습](08_building_and_operating_kafka_connect_pipelines.md)

같은 셸에서 다음을 실행한다. `REPLICATION SLAVE`는 binlog 스트림 읽기에, `REPLICATION CLIENT`는 파일과 위치 조회에 사용한다. `SELECT`, `SHOW DATABASES`, `RELOAD`는 초기 스냅샷에 필요한 데이터·메타데이터 조회와 잠금에 사용한다. 전역 읽기 잠금 대신 테이블 잠금을 사용하는 환경에서는 대상 테이블에 `LOCK TABLES` 권한도 필요하다. 아래 계정은 격리된 로컬 실습용이다. [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [MySQL 8.4 · SHOW BINARY LOG STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-binary-log-status.html)

```bash
mysql_cdc_compose() { docker compose -f compose.yaml -f compose.mysql-cdc.yaml "$@"; }
mysql_cdc_sql() {
  mysql_cdc_compose exec -T mysql-source sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$@"' sh "$@"
}
mysql_cdc_compose up -d --wait
connect_url=http://127.0.0.1:18083

mysql_cdc_sql <<'SQL'
CREATE DATABASE shop;
CREATE TABLE shop.orders (
    id BIGINT PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    amount DECIMAL(12,2)
);
INSERT INTO shop.orders (id, status, amount) VALUES (1, 'created', 12.30);
CREATE USER 'cdc'@'%' IDENTIFIED BY 'local-mysql-cdc';
GRANT SELECT, SHOW DATABASES, RELOAD, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'cdc'@'%';
SELECT @@GLOBAL.log_bin, @@GLOBAL.binlog_format, @@GLOBAL.binlog_row_image, @@GLOBAL.server_id;
SHOW BINARY LOG STATUS;
SQL

curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -e 'any(.[]; .class == "io.debezium.connector.mysql.MySqlConnector")'
```

## 3. REST API로 소스를 등록한다

내부 스키마 이력 토픽은 Debezium이 해당 binlog 위치의 테이블 구조를 복원하는 데 사용한다. 순서 보존을 위해 파티션 하나를 두고 전체 이력을 보관한다. `include.schema.changes=true`로 발행하는 외부용 DDL 이벤트는 별도 토픽 `mysql-cdc`에 기록된다. [Debezium · Configuring Debezium Topics](https://debezium.io/documentation/reference/3.7/install-kafka-connect.html#configuring-debezium-topics) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html)

```bash
mysql_cdc_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic mysql-cdc-schema-history --partitions 1 --replication-factor 1 \
  --config cleanup.policy=delete --config retention.ms=-1 --config retention.bytes=-1

cat > shop-mysql-source.json <<'JSON'
{
  "connector.class": "io.debezium.connector.mysql.MySqlConnector",
  "tasks.max": "1",
  "database.hostname": "mysql-source",
  "database.port": "3306",
  "database.user": "cdc",
  "database.password": "local-mysql-cdc",
  "database.server.id": "184054",
  "database.include.list": "shop",
  "table.include.list": "shop[.]orders",
  "topic.prefix": "mysql-cdc",
  "snapshot.mode": "initial",
  "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
  "schema.history.internal.kafka.topic": "mysql-cdc-schema-history",
  "include.schema.changes": "true",
  "tombstones.on.delete": "true",
  "topic.creation.default.replication.factor": "1",
  "topic.creation.default.partitions": "1"
}
JSON

curl -fsS -X PUT -H 'Content-Type: application/json' \
  "$connect_url/connectors/shop-mysql-source/config" --data-binary @shop-mysql-source.json
curl -fsS "$connect_url/connectors/shop-mysql-source/status" | jq '{connector, tasks}'
```

## 4. `before`, `after`, `op`을 확인한다

커넥터와 작업이 `RUNNING`이면 `mysql_cdc_read 1`에서 스냅샷 행을 확인하고 이어서 같은 키를 INSERT, UPDATE, DELETE 한다. JSON Converter는 키와 값에 `schema`와 `payload`를 넣는다. 기본 키 `id`는 키의 `payload.id`에서 확인한다. tombstone의 Kafka 값은 실제 `null`이다. [Debezium · MySQL Change Events](https://debezium.io/documentation/reference/3.7/connectors/mysql.html#mysql-change-events) · [Apache Kafka · JsonConverter Configuration](https://github.com/apache/kafka/blob/trunk/connect/json/src/main/java/org/apache/kafka/connect/json/JsonConverterConfig.java)

| Kafka 값 | `op` | `before` | `after` |
| --- | --- | --- | --- |
| 스냅샷 | `r` | `null` | 스냅샷의 행 |
| INSERT | `c` | `null` | 추가한 행 |
| UPDATE | `u` | 변경 전 행 | 변경 후 행 |
| DELETE | `d` | 삭제 전 행 | `null` |
| tombstone | 해당 없음 | 해당 없음 | 해당 없음 |

```bash
mysql_cdc_read() {
  mysql_cdc_compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:29092 --topic "${2:-mysql-cdc.shop.orders}" \
    --from-beginning --max-messages "$1" --timeout-ms 30000 \
    --formatter-property print.key=true
}
mysql_cdc_read 1 | cut -f2- | jq -e '.payload.op == "r" and .payload.after.id == 1'

mysql_cdc_sql shop <<'SQL'
INSERT INTO orders (id, status, amount) VALUES (2, 'created', 24.50);
UPDATE orders SET status = 'paid' WHERE id = 2;
DELETE FROM orders WHERE id = 2;
SQL

mysql_cdc_read 5 | jq -Rse '
  split("\n") | map(select(length > 0) | split("\t") | map(fromjson))
  | (map(.[1].payload.op) == ["r","c","u","d",null])
    and (.[1:] | map(.[0].payload.id) == [2,2,2,2])
    and (.[2][1].payload.before.status == "created" and .[2][1].payload.after.status == "paid")
    and (.[3][1].payload.before.status == "paid" and .[3][1].payload.after == null and .[4][1] == null)'
```

## 5. JDBC Sink에 행 값과 삭제를 전달한다

Confluent JDBC Sink가 대상 컬럼에 쓸 수 있도록 `ExtractNewRecordState` SMT로 `after` 구조체를 꺼낸다. 소스에 SMT를 붙이면 Kafka에 저장되는 레코드가 행 형태로 바뀐다. 싱크에 붙이면 원본 토픽의 `before`, `after`, `op`, `source`를 보존하면서 JDBC 경로에만 행 형태를 적용한다. 다음은 37번 실습에서 사용하는 싱크 설정의 일부다. [Debezium · New Record State Extraction](https://github.com/debezium/debezium/blob/main/documentation/modules/ROOT/pages/transformations/event-flattening.adoc) · [MySQL에서 PostgreSQL로 복제](37_replicating_mysql_changes_to_postgresql_with_kafka_connect.md)

```properties
topics=mysql-cdc.shop.orders
transforms=unwrap
transforms.unwrap.type=io.debezium.transforms.ExtractNewRecordState
transforms.unwrap.delete.tombstone.handling.mode=tombstone
insert.mode=upsert
pk.mode=record_key
pk.fields=id
delete.enabled=true
```

이 설정은 INSERT·UPDATE·스냅샷을 `id` 기준으로 upsert한다. DELETE의 envelope는 SMT에서 제거되고 같은 키의 tombstone은 JDBC Sink에 전달되어 해당 행을 삭제한다. 싱크도 스키마가 켜진 JSON Converter를 사용해야 키 구조체와 `Decimal` 같은 논리 타입을 복원할 수 있다. [Confluent · JDBC Sink Configuration](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)
