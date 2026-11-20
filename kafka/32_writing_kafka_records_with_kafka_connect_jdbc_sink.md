# Writing Kafka Records with Kafka Connect JDBC Sink

Confluent JDBC Sink는 Kafka 레코드의 키와 값 스키마를 사용해 대상 DB의 기본키와 쓸 컬럼을 정한다. 31번의 `jdbc.mysql.orders`를 읽어 MySQL의 `shop_sink.orders_copy`에 저장하고, 같은 주문이 다시 들어오거나 삭제될 때의 동작을 확인한다. [31번 JDBC Source](31_ingesting_mysql_changes_with_kafka_connect_jdbc_source.md) · [Confluent · JDBC Sink](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

## 1. 대상 테이블과 REST 헬퍼 준비하기

31번의 Compose 환경과 같은 셸에서 실행한다. Connect는 `127.0.0.1:18083`에서 응답하고, `jdbc_compose`, `jdbc_mysql`, `jdbc_orders_read`를 사용할 수 있어야 한다. `jdbc.mysql.orders`에는 키가 있는 실습 레코드가 있어야 한다. 같은 MySQL 서버에 목적지 전용 데이터베이스와 쓰기 계정을 만든다. [08번 Connect REST API](08_building_and_operating_kafka_connect_pipelines.md#5-rest-api와-웹-화면으로-운영하기)

```bash
jdbc_mysql <<'SQL'
CREATE DATABASE shop_sink;
CREATE TABLE shop_sink.orders_copy (
    id BIGINT NOT NULL PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    business_date DATE NOT NULL,
    scheduled_at DATETIME(3) NOT NULL,
    updated_at TIMESTAMP(3) NOT NULL
);
CREATE USER 'orders_writer'@'%' IDENTIFIED BY 'orders-writer-local';
GRANT SELECT, INSERT, UPDATE, DELETE ON shop_sink.orders_copy TO 'orders_writer'@'%';
SQL

connect_url=http://127.0.0.1:18083
connect_rest() {
  local method=$1 path=$2
  shift 2
  curl -fsS -X "$method" -H 'Content-Type: application/json' "$connect_url/$path" "$@"
}
```

## 2. 키, 스키마, 쓰기 모드 맞추기

31번에서 단일 키는 Connect `int64`이고 값은 주문 컬럼을 가진 Struct다. 예를 들어 키 `1`은 `{"schema":{"type":"int64","optional":false},"payload":1}`로 전달된다. 양쪽에 `JsonConverter`와 `schemas.enable=true`를 설정해야 이 JSON에서 키 타입과 값의 `Decimal`, `Date`, `Timestamp` 논리 타입을 복원한다. primitive 키를 `record_key`로 사용하면 `pk.fields`에 대상 컬럼 이름 하나를 지정한다. 키가 Struct라면 `pk.fields=tenant_id,id`처럼 사용할 키 필드를 고른다. 값을 기준으로 키를 뽑는 `record_value` 모드에서는 값이 null인 삭제 레코드에서 키를 복원할 수 없다. [Confluent · 데이터 매핑과 키](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#data-mapping) · [Confluent · JDBC Sink 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)

| `insert.mode` | 기록 방식 | 이 예제에서 같은 `id`를 다시 읽을 때 |
| --- | --- | --- |
| `insert` | 새 행을 삽입한다. | 기본키 충돌이 발생한다. |
| `update` | 지정한 키와 일치하는 기존 행을 갱신한다. | 기존 행만 바뀐다. 없는 키의 행은 생성되지 않는다. |
| `upsert` | 키가 있으면 갱신하고 없으면 삽입한다. | MySQL은 `INSERT … ON DUPLICATE KEY UPDATE`를 사용한다. |

아래에서는 `upsert`로 최신 상태를 저장한다. Kafka 레코드가 재전달되더라도 같은 기본키로 행을 쓰므로 중복 행은 생기지 않는다. 오래된 레코드를 나중에 재생하면 더 새로운 상태를 덮을 수 있으므로 같은 키의 순서를 유지한다. 자동 DDL을 끄고 준비한 테이블에 기록하며, `table.name.format`을 고정해 점이 있는 토픽 이름을 그대로 테이블 이름으로 해석하는 일을 피한다. [Confluent · JDBC Sink 전달과 upsert](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

```bash
connect_rest PUT connectors/jdbc-mysql-sink/config --data-binary @- <<'JSON'
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "tasks.max": "1",
  "topics": "jdbc.mysql.orders",
  "connection.url": "jdbc:mysql://mysql-jdbc:3306/shop_sink?connectionTimeZone=SERVER",
  "connection.user": "orders_writer",
  "connection.password": "orders-writer-local",
  "table.name.format": "orders_copy",
  "auto.create": "false",
  "auto.evolve": "false",
  "insert.mode": "upsert",
  "pk.mode": "record_key",
  "pk.fields": "id",
  "delete.enabled": "true",
  "db.timezone": "UTC",
  "date.timezone": "UTC",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "true"
}
JSON

connect_rest GET connectors/jdbc-mysql-sink/status | jq .
jdbc_mysql shop_sink -e 'SELECT id, status, amount FROM orders_copy ORDER BY id'
jdbc_mysql shop -e "UPDATE orders SET status='shipped' WHERE id=1"
```

커넥터와 작업이 `RUNNING`이 된 뒤 같은 `SELECT`를 다시 실행한다. 폴링 및 싱크 기록을 거치면 `id=1` 한 행이 `shipped`로 갱신되고 `id=2`의 `amount=24.60`이 유지된다. `FAILED` 상태라면 작업의 `trace`에서 키 스키마, DB 연결, 대상 테이블 오류를 먼저 확인한다. [Apache Kafka · Connect Administration](https://kafka.apache.org/43/kafka-connect/administration/)

## 3. tombstone으로 대상 행 삭제하기

`delete.enabled=true`와 `pk.mode=record_key`를 함께 사용하면, 값이 Kafka 수준에서 null인 레코드를 받았을 때 키에 해당하는 행을 삭제한다. JDBC Source의 SQL 폴링은 MySQL의 물리 삭제를 발행하지 않으므로 이 실습에서는 Kafka CLI로 삭제 레코드를 보낸다. 콘솔에서 읽은 실제 키를 그대로 사용하면 파티셔닝과 compaction에 쓰이는 키 바이트까지 동일하다. [Confluent · Delete mode](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#delete-mode) · [Apache Kafka · LineMessageReader](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/LineMessageReader.java)

```bash
(
  set -eu
  order_key=$(jdbc_orders_read 1 | cut -f1)
  printf '%s\n' "$order_key" | jq -e '.schema.type == "int64" and .payload == 1' >/dev/null

  printf '%s\t%s\n' "$order_key" '__TOMBSTONE__' |
    jdbc_compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
      --bootstrap-server kafka:29092 --topic jdbc.mysql.orders \
      --reader-property parse.key=true --reader-property null.marker=__TOMBSTONE__
)

jdbc_mysql shop_sink -e 'SELECT id, status FROM orders_copy ORDER BY id'
```

`null.marker`가 입력 토큰을 실제 null 값으로 보낸다. 싱크가 해당 레코드를 처리하면 대상에서 `id=1`이 사라지고 `id=2`만 남는다. 이후 소스의 `id=1`이 수정되거나 소스 커서를 초기화해 다시 발행되면 대상에 재삽입된다. 소스의 실제 삭제까지 동기화하는 구성은 MySQL binlog를 사용한다. [37번 MySQL에서 PostgreSQL로 CDC 복제](37_replicating_mysql_changes_to_postgresql_with_kafka_connect.md)

## 4. DATE, DATETIME, TIMESTAMP 비교하기

`db.timezone=UTC`는 JDBC의 시간 값 바인딩에 적용되고 `date.timezone=UTC`는 DATE를 날짜 경계 이동 없이 바인딩한다. 소스와 싱크의 MySQL 세션은 `+00:00`을 사용한다. 아래에서는 이미 기록된 `id=2`를 세션 시간대만 바꿔 읽는다. [Confluent · 시간대 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html) · [MySQL · DATE, DATETIME, TIMESTAMP](https://dev.mysql.com/doc/refman/8.4/en/datetime.html)

```bash
jdbc_mysql shop_sink <<'SQL'
SET time_zone = '+00:00';
SELECT @@session.time_zone, business_date, scheduled_at, updated_at,
       UNIX_TIMESTAMP(updated_at) AS updated_epoch FROM orders_copy WHERE id = 2;
SET time_zone = '-08:00';
SELECT @@session.time_zone, business_date, scheduled_at, updated_at,
       UNIX_TIMESTAMP(updated_at) AS updated_epoch FROM orders_copy WHERE id = 2;
SQL
```

| 세션 | `business_date` (`DATE`) | `scheduled_at` (`DATETIME(3)`) | `updated_at` (`TIMESTAMP(3)`) |
| --- | --- | --- | --- |
| `+00:00` | `2025-01-01` | `2025-01-01 09:00:00.123` | `2025-01-01 00:30:00.123` |
| `-08:00` | `2025-01-01` | `2025-01-01 09:00:00.123` | `2024-12-31 16:30:00.123` |

두 세션의 `updated_epoch`는 `1735691400.123`으로 같아야 한다. `DATE`는 달력 날짜를, `DATETIME`은 벽시계 시각을, `TIMESTAMP`는 세션 시간대로 변환한 시각을 반환한다. 값이 예상과 다르면 UTC로 정한 소스의 벽시계 계약, Connector/J가 인식한 세션 시간대, 싱크의 시간대 설정을 함께 점검한다. [MySQL · Connector/J 시간대 변환](https://dev.mysql.com/doc/connector-j/en/connector-j-time-instants.html)
