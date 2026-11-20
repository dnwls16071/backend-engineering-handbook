# Ingesting MySQL Changes with Kafka Connect JDBC Source

Confluent JDBC Source는 MySQL에 주기적으로 `SELECT`를 실행하고 결과의 각 행을 Kafka 레코드로 발행한다. 주문 테이블의 `updated_at`과 `id`를 커서로 사용해 새 행과 수정된 행을 `jdbc.mysql.orders`로 가져온다. 폴링 사이에 같은 행이 여러 번 바뀌면 조회 시점에 남은 상태를 읽는다. [Confluent · JDBC Source](https://docs.confluent.io/kafka-connectors/jdbc/current/source-connector/overview.html)

## 1. MySQL과 JDBC 플러그인 준비하기

01번과 08번의 `compose.yaml`, `compose.connect.yaml`, `connect-worker.properties`가 있는 로컬 실습 디렉터리에서 시작한다. Docker Compose, `curl`, `jq`가 필요하다. Confluent Marketplace에서 JDBC Source/Sink 10.9.10 ZIP을 내려받아 `connect-plugins/jdbc` 아래에 번들의 `lib` 디렉터리가 오도록 푼다. 공식 MySQL Connector/J 9.7.0 JAR를 같은 `lib`에 넣는다. Maven이 있다면 `mvn dependency:copy -Dartifact=com.mysql:mysql-connector-j:9.7.0 -DoutputDirectory="$PWD/connect-plugins/jdbc/lib"`로 받는다. [08번 Connect 워커](08_building_and_operating_kafka_connect_pipelines.md) · [Confluent Marketplace · JDBC Connector](https://www.confluent.io/hub/confluentinc/kafka-connect-jdbc) · [Confluent · JDBC 드라이버](https://docs.confluent.io/kafka-connectors/jdbc/current/jdbc-drivers.html) · [MySQL · Connector/J Maven 설치](https://dev.mysql.com/doc/connector-j/en/connector-j-installing-maven.html)

`connect-worker.properties`의 `plugin.path`에 `/opt/connect-plugins`를 추가한다. 08번의 FileStream 실습을 이어서 사용하려면 기존 JAR 경로와 쉼표로 연결한다. JDBC 커넥터와 드라이버는 작업을 할당받을 수 있는 모든 워커에 함께 설치하고 워커를 다시 시작한다. 드라이버를 별도의 플러그인 폴더에 두면 커넥터의 클래스 로더가 해당 JAR를 찾지 못할 수 있다. [Apache Kafka · 플러그인 설치](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Confluent · JDBC 드라이버](https://docs.confluent.io/kafka-connectors/jdbc/current/jdbc-drivers.html)

아래를 `compose.jdbc.yaml`로 저장한다. MySQL은 Compose 네트워크 내부에서 `mysql-jdbc:3306`으로 접근한다. 예시 계정과 비밀번호는 로컬 실습용이다. [Docker 공식 MySQL 이미지](https://hub.docker.com/_/mysql)

```yaml
services:
  connect:
    volumes:
      - "./connect-plugins:/opt/connect-plugins:ro"
  mysql-jdbc:
    image: mysql:8.4
    command: ["--default-time-zone=+00:00"]
    environment:
      MYSQL_ROOT_PASSWORD: mysql-jdbc-local
      MYSQL_DATABASE: shop
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "--silent"]
      interval: 2s
      timeout: 3s
      retries: 30
```

```bash
jdbc_compose() {
  docker compose -f compose.yaml -f compose.connect.yaml -f compose.jdbc.yaml "$@"
}

jdbc_mysql() {
  jdbc_compose exec -T mysql-jdbc sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$@"' sh "$@"
}

jdbc_compose up -d --wait
jdbc_compose restart connect
connect_url=http://127.0.0.1:18083
curl -fsS --retry 20 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -er '.[] | select(.class | startswith("io.confluent.connect.jdbc.")) | .class'

jdbc_mysql shop <<'SQL'
CREATE TABLE orders (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    business_date DATE NOT NULL,
    scheduled_at DATETIME(3) NOT NULL,
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX orders_poll (updated_at, id)
);
CREATE USER 'orders_reader'@'%' IDENTIFIED BY 'orders-reader-local';
GRANT SELECT ON shop.orders TO 'orders_reader'@'%';
INSERT INTO orders (id, status, amount, business_date, scheduled_at, updated_at) VALUES
    (1, 'created', 12.30, '2025-01-01', '2025-01-01 09:00:00.123', '2025-01-01 00:30:00.123'),
    (2, 'created', 24.60, '2025-01-01', '2025-01-01 09:00:00.123', '2025-01-01 00:30:00.123');
SQL

jdbc_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --if-not-exists --topic jdbc.mysql.orders \
  --partitions 1 --replication-factor 1
```

## 2. 폴링 기준과 타입 정하기

| `mode` | 쿼리 기준 | 관찰할 수 있는 변경 |
| --- | --- | --- |
| `bulk` | 매번 전체 조회 | 현재 존재하는 행을 매번 발행한다. |
| `incrementing` | 마지막 값보다 큰 정수 컬럼 | 증가하는 ID가 붙은 삽입을 읽는다. |
| `timestamp` | 마지막 시간보다 뒤인 수정 시각 | 삽입과 수정을 읽는다. 여러 행의 시각이 같으면 장애나 조회 한도에서 누락될 수 있다. |
| `timestamp+incrementing` | `(수정 시각, ID)` | 같은 시각의 여러 행을 ID로 구분한다. |

이 실습의 두 행은 `updated_at`이 같아도 `(updated_at, id)`가 다르다. 다음 조회는 큰 타임스탬프 또는 같은 타임스탬프의 더 큰 ID부터 읽는다. `timestamp.delay.interval.ms=2000`이면 DB 현재 시각보다 최소 2초 이전의 행을 조회해 먼저 시각이 부여된 트랜잭션에 커밋할 시간을 준다. 그보다 늦게 커밋되거나 커서보다 오래된 시각으로 기록된 행은 건너뛸 수 있다. `AUTO_INCREMENT`의 ID 할당 순서도 커밋 순서와 다를 수 있다. 물리 삭제, 모든 중간 상태, 트랜잭션 단위 변경 이력이 필요하면 binlog 기반 CDC를 사용한다. [Confluent · 증분 조회 모드](https://docs.confluent.io/kafka-connectors/jdbc/current/source-connector/overview.html#incremental-query-modes) · [33번 MySQL binlog CDC](33_capturing_mysql_binlog_changes_with_debezium.md)

`numeric.mapping=none`은 `DECIMAL(12,2)`의 정밀도를 Connect `Decimal`로 보존한다. schemaful JSON에서는 기본 `BASE64` 표현과 `scale`이 함께 전달된다. `business_date`는 날짜를 나타내는 Connect `Date`이고, MySQL `DATETIME`과 `TIMESTAMP`는 이 조합에서 Connect `Timestamp`로 읽힌다. `db.timezone=UTC`를 MySQL 세션 시간대에 맞추고 `timestamp.granularity=connect_logical`을 사용해 밀리초로 전달한다. MySQL `DATETIME`은 벽시계 값이므로 UTC 적용은 이 실습의 계약이다. 원본 컬럼에 마이크로초가 있다면 출력 정밀도와 싱크가 받아들이는 타입을 함께 결정한다. [Confluent · JDBC Source 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/source-connector/source_config_options.html) · [MySQL · DATE, DATETIME, TIMESTAMP](https://dev.mysql.com/doc/refman/8.4/en/datetime.html) · [MySQL · Connector/J 시간대 변환](https://dev.mysql.com/doc/connector-j/en/connector-j-time-instants.html)

## 3. 키와 토픽을 변환하고 레코드 확인하기

JDBC Source의 기본 키는 null이다. `ValueToKey`가 값의 `id`를 키 Struct로 복사하고 `ExtractField$Key`가 그 안의 `id`를 primitive `int64` 키로 꺼낸다. 여러 컬럼이 키인 테이블에서는 `ValueToKey.fields`에 `tenant_id,id`처럼 적고 `ExtractField$Key`를 생략해 두 필드를 가진 Struct 키를 유지한다. `RegexRouter`는 발행 전에 `mysql-poll.orders`를 `jdbc.mysql.orders`로 바꾼다. 이미 발행된 레코드는 기존 토픽에 남는다. [Confluent · ValueToKey](https://docs.confluent.io/kafka-connectors/transforms/current/valuetokey.html) · [Confluent · ExtractField](https://docs.confluent.io/kafka-connectors/transforms/current/extractfield.html) · [Confluent · RegexRouter](https://docs.confluent.io/kafka-connectors/transforms/current/regexrouter.html)

```bash
source_url="$connect_url/connectors/jdbc-mysql-source"
curl -fsS -X PUT -H 'Content-Type: application/json' "$source_url/config" --data-binary @- <<'JSON'
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
  "tasks.max": "1",
  "connection.url": "jdbc:mysql://mysql-jdbc:3306/shop?connectionTimeZone=SERVER",
  "connection.user": "orders_reader",
  "connection.password": "orders-reader-local",
  "catalog.pattern": "shop",
  "table.whitelist": "shop.orders",
  "mode": "timestamp+incrementing",
  "incrementing.column.name": "id",
  "timestamp.column.name": "updated_at",
  "timestamp.delay.interval.ms": "2000",
  "poll.interval.ms": "1000",
  "db.timezone": "UTC",
  "numeric.mapping": "none",
  "timestamp.granularity": "connect_logical",
  "topic.prefix": "mysql-poll.",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "true",
  "transforms": "makeKey,extractId,routeOrders",
  "transforms.makeKey.type": "org.apache.kafka.connect.transforms.ValueToKey",
  "transforms.makeKey.fields": "id",
  "transforms.extractId.type": "org.apache.kafka.connect.transforms.ExtractField$Key",
  "transforms.extractId.field": "id",
  "transforms.routeOrders.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.routeOrders.regex": "^mysql-poll[.](orders)$",
  "transforms.routeOrders.replacement": "jdbc.mysql.$1"
}
JSON

curl -fsS "$source_url/status" | jq .

jdbc_orders_read() {
  jdbc_compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:29092 --topic jdbc.mysql.orders --from-beginning \
    --formatter-property print.key=true --timeout-ms 15000 --max-messages "$1"
}

jdbc_orders_read 2
jdbc_mysql shop -e "UPDATE orders SET status='paid' WHERE id=1"
jdbc_orders_read 3
```

`status` 응답에서 커넥터와 작업이 `RUNNING`인지 확인한다. 첫 두 레코드의 키는 `payload`가 각각 `1`, `2`인 `int64` JSON이다. 다음 조회에서 같은 키 `1`로 `status=paid`가 추가되고 키 `2`의 초기 상태는 유지된다. 이 JSON의 키와 값에 붙은 스키마를 32번 JDBC Sink가 DB 컬럼과 기본키를 결정하는 데 사용한다. [32번 JDBC Sink](32_writing_kafka_records_with_kafka_connect_jdbc_sink.md)

## 4. 지정한 소스의 커서만 초기화하기

실습 토픽의 재발행을 확인할 때만 아래를 실행한다. 연결된 싱크가 있다면 먼저 중지하고 중복 반영 범위를 확인한다. Connect에서 이 소스 커넥터를 `STOPPED` 상태로 전환하고 마지막 저장 오프셋을 보관한 뒤 삭제한다. `DELETE` 요청의 범위는 경로에 지정한 커넥터의 소스 커서다. `timestamp.initial`을 지정하지 않은 예제는 재개하면 테이블에 남은 행을 처음부터 다시 조회하고 토픽에 추가한다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [Confluent · JDBC Source 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/source-connector/source_config_options.html)

```bash
(
  set -eu
  curl -fsS -X PUT "$source_url/stop"
  for attempt in {1..30}; do
    if curl -fsS "$source_url/status" |
      jq -e '.connector.state == "STOPPED" and (.tasks | length == 0)' >/dev/null; then
      break
    fi
    if [ "$attempt" -eq 30 ]; then
      printf '%s\n' 'Connector did not stop' >&2
      exit 1
    fi
    sleep 1
  done

  saved_offsets=$(mktemp ./jdbc-mysql-source-offsets.XXXXXX)
  curl -fsS "$source_url/offsets" > "$saved_offsets"
  jq -e '.offsets | type == "array"' "$saved_offsets" >/dev/null
  printf 'Saved offsets in %s\n' "$saved_offsets"

  curl -fsS -X DELETE "$source_url/offsets"
  curl -fsS "$source_url/offsets" | jq -e '.offsets == []'
  curl -fsS -X PUT "$source_url/resume"
)
```

여러 테이블을 읽는 커넥터에서 한 소스 파티션만 다시 읽으려면 `GET …/offsets`의 해당 `partition` 객체를 그대로 사용해 `PATCH …/offsets`의 해당 `offset`에 `null`을 지정한다. 소스 파티션의 JSON 형식은 커넥터가 정한다. 재개 전이라면 저장한 응답을 `PATCH …/offsets`에 전달해 이전 커서를 복구할 수 있다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)
