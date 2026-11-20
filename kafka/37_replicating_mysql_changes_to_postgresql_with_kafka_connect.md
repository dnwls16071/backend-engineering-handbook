# Replicating MySQL Changes to PostgreSQL with Kafka Connect

Debezium이 MySQL `shop.orders`의 스냅샷과 binlog 변경을 `mysql-cdc.shop.orders`로 보낸다. Confluent JDBC Sink는 이 토픽만 구독하고 `ExtractNewRecordState`로 행 데이터를 꺼내 PostgreSQL `public.orders_replica`에 반영한다. Kafka에 Debezium의 원본 이벤트가 남아 다른 소비자는 변경 전후 값과 메타데이터도 읽을 수 있다. [33번 MySQL binlog CDC](33_capturing_mysql_binlog_changes_with_debezium.md) · [Debezium · New Record State Extraction](https://debezium.io/documentation/reference/stable/transformations/event-flattening.html)

## 1. PostgreSQL과 싱크 플러그인 준비하기

33번의 `compose.yaml`, `compose.mysql-cdc.yaml`을 사용한다. `shop-mysql-source`가 `connect-cdc` 워커에서 실행되고 `mysql-cdc.shop.orders`에 schemaful JSON으로 발행하는 상태에서 시작한다. 원본 레코드의 값에 Debezium envelope가 있고 삭제 시 tombstone이 발행되어야 한다. 36번에서 Avro로 바꾼 토픽은 싱크의 Converter도 그 형식에 맞춰야 한다. 로컬 실습에서는 33번 JSON 토픽을 사용한다. [33번 MySQL CDC 실습](33_capturing_mysql_binlog_changes_with_debezium.md) · [36번 Avro와 Schema Registry](36_integrating_kafka_connect_with_avro_and_schema_registry.md)

31번에서 확보한 Confluent JDBC 플러그인의 `connect-plugins/jdbc/lib`에 JDBC 커넥터 JAR와 PostgreSQL JDBC 드라이버가 있는지 확인한다. Confluent JDBC 플러그인 번들에 PostgreSQL 드라이버가 포함돼 있다. `ExtractNewRecordState`도 싱크 작업을 맡을 수 있는 모든 워커의 플러그인 경로에서 로드돼야 한다. 이 실습은 Debezium Connect 이미지에 포함된 변환을 사용하고, JDBC 플러그인 디렉터리만 추가한다. [31번 JDBC 플러그인 설치](31_ingesting_mysql_changes_with_kafka_connect_jdbc_source.md#1-mysql과-jdbc-플러그인-준비하기) · [Confluent · JDBC 드라이버](https://docs.confluent.io/kafka-connectors/jdbc/current/jdbc-drivers.html) · [Debezium · Kafka Connect 설치](https://debezium.io/documentation/reference/3.7/install-kafka-connect.html)

아래를 `compose.postgres-cdc.yaml`로 저장한다. PostgreSQL은 Compose 네트워크의 `postgres-cdc:5432`로 접근하고, Connect REST 주소는 33번에서 사용한 `127.0.0.1:18083`이다. 실습 DB 계정의 비밀번호는 아래 값으로 고정한다. [Docker 공식 PostgreSQL 이미지](https://hub.docker.com/_/postgres)

```yaml
services:
  connect-cdc:
    volumes:
      - "./connect-plugins/jdbc/lib:/kafka/connect/jdbc:ro"
  postgres-cdc:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: shop_replica
      POSTGRES_PASSWORD: pg-cdc-local
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "postgres", "-d", "shop_replica"]
      interval: 2s
      timeout: 3s
      retries: 20
```

```bash
pg_cdc_compose() {
  docker compose -f compose.yaml -f compose.mysql-cdc.yaml -f compose.postgres-cdc.yaml "$@"
}

pg_cdc_sql() {
  pg_cdc_compose exec -T postgres-cdc psql -U postgres -d shop_replica -v ON_ERROR_STOP=1 "$@"
}

pg_cdc_compose up -d --wait connect-cdc postgres-cdc
connect_url=http://127.0.0.1:18083
curl -fsS --retry 20 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -er '.[] | select(.class == "io.confluent.connect.jdbc.JdbcSinkConnector") | .class'

pg_cdc_sql <<'SQL'
CREATE TABLE public.orders_replica (
    id BIGINT PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    amount NUMERIC(12,2)
);
CREATE ROLE pg_sink LOGIN PASSWORD 'pg-sink-local';
GRANT USAGE ON SCHEMA public TO pg_sink;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.orders_replica TO pg_sink;
SQL
```

## 2. Debezium 이벤트를 PostgreSQL 행에 매핑하기

`ExtractNewRecordState`는 스냅샷(`r`), 삽입(`c`), 수정(`u`) 이벤트의 `after`를 값 Struct로 전달한다. `delete.tombstone.handling.mode=tombstone`은 삭제 envelope(`d`)를 버리고 같은 키의 뒤따르는 tombstone을 유지한다. 싱크는 `delete.enabled=true`와 `pk.mode=record_key`를 사용해 이 tombstone을 `DELETE`로 바꾼다. `rewrite` 모드는 삭제 마커가 있는 값 Struct를 만들므로 이 upsert 설정에서는 행 삭제로 이어지지 않는다. 싱크 구독을 주문 토픽 하나로 제한해 heartbeat, 트랜잭션, 스키마 변경 토픽을 처리 대상에서 제외한다. [Debezium · 삭제 이벤트 변환](https://debezium.io/documentation/reference/stable/transformations/event-flattening.html) · [Confluent · JDBC Sink Delete mode](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#delete-mode)

```bash
pg_sink_url="$connect_url/connectors/shop-orders-pg-sink"
curl -fsS -X PUT -H 'Content-Type: application/json' "$pg_sink_url/config" --data-binary @- <<'JSON'
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "tasks.max": "1",
  "topics": "mysql-cdc.shop.orders",
  "connection.url": "jdbc:postgresql://postgres-cdc:5432/shop_replica",
  "connection.user": "pg_sink",
  "connection.password": "pg-sink-local",
  "table.name.format": "public.orders_replica",
  "insert.mode": "upsert",
  "pk.mode": "record_key",
  "pk.fields": "id",
  "delete.enabled": "true",
  "auto.create": "false",
  "auto.evolve": "false",
  "db.timezone": "UTC",
  "date.timezone": "UTC",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "true",
  "transforms": "unwrap",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.unwrap.delete.tombstone.handling.mode": "tombstone"
}
JSON

curl -fsS "$pg_sink_url/status" | jq .
pg_cdc_sql -c 'SELECT id, status, amount FROM public.orders_replica ORDER BY id'
```

값 Struct의 컬럼 이름으로 대상 테이블을 채우고, Debezium 키 Struct의 `id`로 PostgreSQL의 `ON CONFLICT (id) DO UPDATE`를 실행한다. 커넥터는 미리 만든 대상 테이블에 기록한다. `RUNNING`을 확인한 뒤 위 조회로 기존 `id=1` 스냅샷 행이 보일 때까지 기다린다. 아래에서는 변경마다 PostgreSQL의 결과를 확인하고 다음 단계로 넘어간다. [Confluent · Idempotent writes](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#idempotent-writes) · [PostgreSQL · INSERT](https://www.postgresql.org/docs/17/sql-insert.html)

```bash
wait_pg_order() {
  local expected=$1 actual attempt
  for attempt in {1..30}; do
    actual=$(pg_cdc_sql -At -c 'SELECT status, amount FROM public.orders_replica WHERE id=101') || return 1
    if [ "$actual" = "$expected" ]; then
      printf '%s\n' "${actual:-<no row>}"
      return 0
    fi
    sleep 1
  done
  printf 'Expected %s, found %s\n' "${expected:-<no row>}" "${actual:-<no row>}" >&2
  return 1
}

(
  set -eu
  mysql_cdc_sql shop -e "INSERT INTO orders (id, status, amount) VALUES (101, 'created', 12.30)"
  wait_pg_order 'created|12.30'

  mysql_cdc_sql shop -e "UPDATE orders SET status='paid', amount=13.45 WHERE id=101"
  wait_pg_order 'paid|13.45'

  mysql_cdc_sql shop -e 'DELETE FROM orders WHERE id=101'
  wait_pg_order ''
)
```

## 3. MySQL과 PostgreSQL의 타입 차이 확인하기

JDBC Sink는 MySQL DDL 대신 변환 후의 Connect 스키마를 보고 PostgreSQL에 값을 바인딩한다. 대상 컬럼의 범위와 정밀도는 미리 정하고, 시간과 이진 데이터는 대표 경곗값을 테스트한다. [Debezium · MySQL 타입 매핑](https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-data-types) · [Confluent · JDBC Sink 타입 매핑](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#auto-creation-and-auto-evolution) · [PostgreSQL · Data Types](https://www.postgresql.org/docs/17/datatype.html)

| MySQL 타입 | PostgreSQL 대상 | 확인할 점 |
| --- | --- | --- |
| `BIGINT` | `BIGINT` | 실습은 signed `BIGINT`를 사용한다. `BIGINT UNSIGNED` 전체 범위가 필요하면 Debezium `bigint.unsigned.handling.mode=precise`와 PostgreSQL `NUMERIC(20,0)`을 검토한다. |
| `VARCHAR(32)` | `VARCHAR(32)` 또는 `TEXT` | 문자열 길이, collation, 고유성 비교 규칙은 대상에서 별도로 정의한다. |
| `DECIMAL(12,2)` | `NUMERIC(12,2)` | Debezium `decimal.handling.mode=precise`에서 Connect `Decimal`을 전달한다. `12.30`처럼 소수 자릿수가 있는 값을 대조한다. |
| `DATETIME` | `TIMESTAMP WITHOUT TIME ZONE` | 벽시계 값이다. Debezium 기본 설정이 내보내는 정수 논리 타입을 싱크가 받아들이는 스키마로 변환하고 정밀도를 검증한다. |
| `TIMESTAMP` | `TIMESTAMPTZ` | Debezium MySQL은 UTC ISO-8601 `ZonedTimestamp` 문자열을 내보낸다. 예를 들어 `TEXT` 스테이징 열에 받은 뒤 PostgreSQL에서 `TIMESTAMPTZ`로 명시적으로 변환할 수 있다. |
| `BINARY`, `VARBINARY` | `BYTEA` | Connect `BYTES`로 전달되도록 `binary.handling.mode=bytes`를 사용하고, 0바이트를 포함한 값을 확인한다. |

## 4. 새 컬럼을 안전하게 추가하기

`auto.create`와 `auto.evolve`를 끈 구성에서는 양쪽의 DDL을 명시적으로 적용한다. JDBC Sink 작업은 대상 테이블의 메타데이터를 캐시하므로 싱크를 중지한 뒤 PostgreSQL에 nullable 컬럼을 만들고, MySQL에 같은 이름의 nullable 컬럼을 추가한다. 싱크를 재개하면 새 작업이 대상 테이블의 메타데이터를 읽고 저장된 Kafka 위치부터 처리한다. 이전 레코드에 새 필드가 없어도 대상에 기록할 수 있다. [Confluent · DbStructure](https://github.com/confluentinc/kafka-connect-jdbc/blob/v10.9.10/src/main/java/io/confluent/connect/jdbc/sink/DbStructure.java#L128) · [Confluent · Auto-creation and Auto-evolution](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#auto-creation-and-auto-evolution) · [PostgreSQL · ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html)

```bash
(
  set -eu
  curl -fsS -X PUT "$pg_sink_url/stop"
  for attempt in {1..30}; do
    if curl -fsS "$pg_sink_url/status" |
      jq -e '.connector.state == "STOPPED" and (.tasks | length == 0)' >/dev/null; then
      break
    fi
    if [ "$attempt" -eq 30 ]; then
      printf '%s\n' 'Connector did not stop' >&2
      exit 1
    fi
    sleep 1
  done

  pg_cdc_sql -c 'ALTER TABLE public.orders_replica ADD COLUMN shipping_note TEXT'
  mysql_cdc_sql shop -e 'ALTER TABLE orders ADD COLUMN shipping_note VARCHAR(80) NULL'
  curl -fsS -X PUT "$pg_sink_url/resume"
  mysql_cdc_sql shop -e "UPDATE orders SET shipping_note='leave at door' WHERE id=1"
)

pg_cdc_sql -c 'SELECT id, shipping_note FROM public.orders_replica WHERE id=1'
```

새 스키마의 CDC 이벤트를 처리하면 `id=1`의 `shipping_note`에 `leave at door`가 보인다. `auto.evolve=true`는 누락된 컬럼을 추가할 수 있다. 타입 변경, 컬럼 삭제·이름 변경, 기본키 변경은 DB 마이그레이션으로 다룬다. 필수 컬럼은 nullable 또는 기본값으로 추가하고, 과거 레코드 재처리와 데이터 채우기를 검증한 뒤 제약을 강화한다. [Confluent · JDBC Sink DDL 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html#ddl-support)
