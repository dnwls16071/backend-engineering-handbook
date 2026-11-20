# Capturing PostgreSQL Changes with Debezium and JDBC Sink

PostgreSQL의 커밋된 행 변경을 Debezium으로 읽고, Kafka Connect의 JDBC Sink에서 다른 PostgreSQL 데이터베이스에 반영한다. Kafka에는 `before`, `after`, `op`가 있는 CDC 이벤트를 보존하고, Sink는 `after`를 행으로 펼쳐 기본 키 기준으로 upsert한다. 삭제는 같은 키의 tombstone으로 반영한다. [Debezium · PostgreSQL Connector](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html) · [Confluent · JDBC Sink Overview](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

## 1. WAL, `pgoutput`, 복제 슬롯, publication

| 구성 요소 | 역할 |
| --- | --- |
| WAL | PostgreSQL이 데이터베이스 변경을 기록하는 로그. 논리 디코딩에는 `wal_level=logical`이 필요하다. |
| `pgoutput` | PostgreSQL에 내장된 논리 디코딩 플러그인. WAL의 변경을 논리 복제 프로토콜로 내보낸다. |
| 논리 복제 슬롯 | 데이터베이스와 플러그인에 연결된 소비 위치. 재개에 필요한 WAL을 보관하므로 작업이 멈췄을 때 보관량도 확인한다. |
| Publication | 발행할 테이블과 연산의 범위. Debezium의 `table.include.list`에도 들어 있는 테이블의 변경이 Kafka로 전달된다. |

복제 슬롯과 WAL 송신 프로세스에 여유가 있도록 `max_replication_slots`와 `max_wal_senders`를 설정한다. Connect의 소스 오프셋과 슬롯을 유지하면 재시작 시 기존 위치부터 읽을 수 있다. `restart_lsn`은 보관에 필요한 WAL의 하한을, `confirmed_flush_lsn`은 논리 슬롯 소비자가 수신을 확인한 위치를 보여준다. [PostgreSQL · Logical Decoding](https://www.postgresql.org/docs/17/logicaldecoding-explanation.html) · [PostgreSQL · Replication Slots](https://www.postgresql.org/docs/17/view-pg-replication-slots.html) · [16번 CDC 복구 실습](16_building_reliable_cdc_pipelines_with_debezium.md#1-재시작에-필요한-상태)

실습에서는 16번 Compose가 초기화한 계정 `cdc`를 쓴다. 권한을 분리할 때는 `LOGIN REPLICATION` 역할에 소스 DB `CONNECT`, 스키마 `USAGE`, 스냅샷할 테이블의 `SELECT`를 부여하고 `pg_hba.conf`에서 소스 DB 접속을 허용한다. 관리자가 publication을 미리 만들면 커넥터는 `publication.autocreate.mode=disabled`로 그 publication을 사용한다. 테이블을 추가하려면 publication을 변경할 권한과 해당 테이블의 소유권이 필요하다. [Debezium · Setting Up PostgreSQL](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html#setting-up-postgresql) · [PostgreSQL · CREATE PUBLICATION](https://www.postgresql.org/docs/17/sql-createpublication.html) · [PostgreSQL · ALTER PUBLICATION](https://www.postgresql.org/docs/17/sql-alterpublication.html)

## 2. PostgreSQL과 Connect 준비

[16번의 Compose 구성](16_building_reliable_cdc_pipelines_with_debezium.md#2-로컬-커넥터-등록)에서 `compose.yaml`과 `compose.cdc.yaml`을 가져온다. 이 실습의 Connect 주소는 `127.0.0.1:18084`다. [08번 FileStream 실습](08_building_and_operating_kafka_connect_pipelines.md#4-docker에서-분산-워커-실행하기)은 `18083`을 사용한다. Confluent Marketplace에서 JDBC Connector `10.9.0` ZIP을 받아 압축을 풀고, `lib`의 JAR 전체를 `plugins/jdbc/`에 둔다. 패키지에는 PostgreSQL JDBC 드라이버가 함께 들어 있다. `compose.pg-jdbc.yaml`을 같은 디렉터리에 저장한다. [Confluent · JDBC Sink 설치](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#install-the-jdbc-sink-connector) · [Confluent · JDBC Drivers](https://docs.confluent.io/kafka-connectors/jdbc/current/jdbc-drivers.html) · [Debezium · Connect 이미지 플러그인 경로](https://github.com/debezium/container-images/blob/main/connect-base/3.7/Dockerfile)

```yaml
services:
  debezium:
    volumes:
      - ./plugins/jdbc:/kafka/connect/jdbc:ro
```

아래 블록은 새 실습의 초기 DDL이다. 소스 DB `cdc`에 테이블과 publication을 만들고, 대상 DB `cdc_sink`는 Sink가 테이블을 만들 수 있게 비워 둔다. 이후 명령은 같은 셸에서 실행한다.

```bash
pg_cdc_compose() { docker compose -f compose.yaml -f compose.cdc.yaml -f compose.pg-jdbc.yaml "$@"; }
pg_cdc_sql() { pg_cdc_compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U cdc -d cdc "$@"; }
pg_sink_sql() { pg_cdc_compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U cdc -d cdc_sink "$@"; }
pg_cdc_compose up -d --wait
pg_cdc_sql <<'SQL'
SHOW wal_level;
CREATE DATABASE cdc_sink;
CREATE TABLE public.orders_pg38 (id bigint PRIMARY KEY, status varchar(30) NOT NULL);
CREATE PUBLICATION pg38_pub FOR TABLE public.orders_pg38;
INSERT INTO public.orders_pg38 (id, status) VALUES (1, 'existing');
SQL

connect=http://127.0.0.1:18084
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect/connector-plugins" |
  jq -e 'map(.class) | index("io.debezium.connector.postgresql.PostgresConnector") != null
                        and index("io.confluent.connect.jdbc.JdbcSinkConnector") != null'
```

## 3. 소스와 JDBC Sink 등록

소스와 Sink 양쪽의 `JsonConverter`에 `schemas.enable=true`를 설정한다. Sink는 스키마가 있는 레코드에서 `id`와 컬럼 타입을 읽는다. `ExtractNewRecordState`를 Sink에 적용하면 Kafka의 원본 CDC 이벤트를 다른 소비자도 사용할 수 있다. `tombstone` 모드는 DELETE 이벤트의 envelope를 걷어내고 원본 tombstone을 넘긴다. Sink의 `delete.enabled=true`와 `pk.mode=record_key`가 이 레코드를 SQL 삭제로 처리한다. [Confluent · Connect와 스키마](https://docs.confluent.io/platform/current/schema-registry/connect.html) · [Debezium · Event Flattening](https://github.com/debezium/debezium/blob/main/documentation/modules/ROOT/pages/transformations/event-flattening.adoc) · [Confluent · JDBC Sink 설정](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)

```bash
cat > pg-source.json <<'JSON'
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "tasks.max": "1",
  "database.hostname": "postgres", "database.port": "5432",
  "database.user": "cdc", "database.password": "local-cdc-password", "database.dbname": "cdc",
  "plugin.name": "pgoutput", "slot.name": "pg38_slot", "slot.drop.on.stop": "false",
  "publication.name": "pg38_pub", "publication.autocreate.mode": "disabled",
  "table.include.list": "public[.]orders_pg38", "topic.prefix": "pg38",
  "snapshot.mode": "initial", "tombstones.on.delete": "true", "skipped.operations": "t",
  "decimal.handling.mode": "precise", "time.precision.mode": "connect",
  "topic.creation.default.replication.factor": "1", "topic.creation.default.partitions": "1",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter", "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter", "value.converter.schemas.enable": "true"
}
JSON

cat > pg-sink.json <<'JSON'
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "tasks.max": "1", "topics": "pg38.public.orders_pg38",
  "connection.url": "jdbc:postgresql://postgres:5432/cdc_sink",
  "connection.user": "cdc", "connection.password": "local-cdc-password",
  "table.name.format": "public.orders_pg38", "insert.mode": "upsert",
  "pk.mode": "record_key", "pk.fields": "id", "delete.enabled": "true",
  "auto.create": "true", "auto.evolve": "true", "db.timezone": "UTC",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter", "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter", "value.converter.schemas.enable": "true",
  "transforms": "unwrap",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.unwrap.delete.tombstone.handling.mode": "tombstone"
}
JSON

pg_put() {
  curl -fsS -X PUT -H 'Content-Type: application/json' \
    "$connect/connectors/$1/config" --data-binary "@$2" | jq -e '.name'
}
pg_put pg38-source pg-source.json
pg_put pg38-sink pg-sink.json
for connector in pg38-source pg38-sink; do
  curl -fsS "$connect/connectors/$connector/status" | jq '{name, connector, tasks}'
done
```

두 작업이 `RUNNING`이고 대상 테이블에 `1 | existing`이 나타날 때까지 조회한다. 이후 변경을 하나씩 커밋하고 다음 변경 전에 대상에서 반영을 확인한다. 삭제 뒤에는 ID `2`가 사라진다. Upsert와 삭제에는 계속 같은 행을 가리키는 키가 필요하다. `UPDATE`·`DELETE`의 전체 이전 행이 필요할 때는 소스의 `REPLICA IDENTITY FULL`을 검토한다. 이 실습은 `skipped.operations=t`로 `TRUNCATE` 이벤트를 건너뛴다. [Debezium · PostgreSQL Connector](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html) · [Confluent · JDBC Sink Upsert](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

```bash
pg_sink_sql -c 'TABLE public.orders_pg38;'
pg_cdc_sql -c "INSERT INTO public.orders_pg38 (id, status) VALUES (2, 'created');"
pg_sink_sql -c 'SELECT id, status FROM public.orders_pg38 WHERE id = 2;'
pg_cdc_sql -c "UPDATE public.orders_pg38 SET status = 'paid' WHERE id = 2;"
pg_sink_sql -c 'SELECT id, status FROM public.orders_pg38 WHERE id = 2;'
pg_cdc_sql -c 'DELETE FROM public.orders_pg38 WHERE id = 2;'
pg_sink_sql -c 'SELECT count(*) FROM public.orders_pg38 WHERE id = 2;'
pg_cdc_sql -c "SELECT slot_name, active, restart_lsn, confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name = 'pg38_slot';"
```

## 4. Publication에 테이블 추가

`ALTER PUBLICATION ... ADD TABLE`로 기존 범위에 테이블을 추가한다. `SET TABLE`은 테이블 목록 전체를 교체하며, `DROP TABLE`은 지정한 테이블을 제외한다. Publication을 바꾼 뒤 `table.include.list`도 갱신한다. 저장된 오프셋으로 재개한 `snapshot.mode=initial`은 새 테이블의 기존 행을 자동으로 읽지 않으므로, 기존 행도 필요하면 별도로 증분 스냅샷을 요청한다. 아래에서는 새 `INSERT`가 별도 토픽으로 나오는지 확인한다. [PostgreSQL · ALTER PUBLICATION](https://www.postgresql.org/docs/17/sql-alterpublication.html) · [Debezium · Ad Hoc Snapshots](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html#postgresql-ad-hoc-snapshots)

```bash
pg_cdc_sql <<'SQL'
CREATE TABLE public.order_items_pg38 (id bigint PRIMARY KEY, sku varchar(30) NOT NULL);
ALTER PUBLICATION pg38_pub ADD TABLE public.order_items_pg38;
SELECT schemaname, tablename FROM pg_publication_tables WHERE pubname = 'pg38_pub';
SQL
jq '."table.include.list" = "public[.]orders_pg38,public[.]order_items_pg38"' pg-source.json > pg-source-expanded.json
pg_put pg38-source pg-source-expanded.json
```

소스 작업이 `RUNNING`으로 돌아오면 새 테이블에 행을 넣는다. 이 실습의 Sink는 주문 토픽 하나를 구독하며, 품목의 캡처 여부는 Kafka에서 확인한다.

```bash
pg_cdc_sql -c "INSERT INTO public.order_items_pg38 VALUES (10, 'SKU-10');"
pg_cdc_compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic pg38.public.order_items_pg38 \
  --from-beginning --max-messages 1 --timeout-ms 30000 |
  jq -e '.payload.op == "c" and .payload.after.sku == "SKU-10"'
```

## 5. 컬럼 추가와 숫자·시간 타입 검증

소스에서 nullable 컬럼을 추가하고 행을 변경한다. Debezium이 새 컬럼을 포함한 데이터 이벤트를 전송하면 `auto.evolve=true`인 Sink가 대상 컬럼을 추가한다. 대상 JDBC 계정에는 이 DDL을 실행할 권한이 필요하다. `auto.evolve`의 범위는 컬럼 추가다. 기존 컬럼의 타입 변경, 컬럼 삭제, 기본 키 변경은 대상 DB 마이그레이션으로 적용한다. [Confluent · Auto-creation and Auto-evolution](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#auto-creation-and-auto-evolution)

```bash
pg_cdc_sql <<'SQL'
ALTER TABLE public.orders_pg38
  ADD COLUMN amount numeric(12,2), ADD COLUMN note varchar(40),
  ADD COLUMN placed_on date, ADD COLUMN created_at timestamp(3), ADD COLUMN paid_at timestamptz;
UPDATE public.orders_pg38 SET amount = 125.40, note = 'card',
  placed_on = DATE '2026-11-21', created_at = TIMESTAMP '2026-11-21 10:30:00.123',
  paid_at = TIMESTAMPTZ '2026-11-21 10:30:00.123456+09' WHERE id = 1;
SQL
```

대상에 새 컬럼이 생기면 `information_schema`에서 타입을, `SELECT`에서 값을 확인한다. 마지막 열은 `2026-11-21 01:30:00.123456`이 된다.

```bash
pg_sink_sql <<'SQL'
SELECT column_name, data_type, numeric_precision, numeric_scale, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'orders_pg38'
ORDER BY ordinal_position;
SELECT amount, note, placed_on, created_at, paid_at::timestamptz AT TIME ZONE 'UTC' AS paid_utc
FROM public.orders_pg38 WHERE id = 1;
SQL
```

| PostgreSQL 소스 | Debezium → Connect | JDBC Sink 자동 DDL 대상 타입 |
| --- | --- | --- |
| `bigint` | `INT64` | `BIGINT` |
| `numeric(12,2)` | `BYTES` + Connect `Decimal` 논리 타입 | `DECIMAL` (`NUMERIC`의 별칭) |
| `varchar(40)` | `STRING` | `TEXT` |
| `date` | `INT32` + Connect `Date`, epoch 이후 일수 | `DATE` |
| `timestamp(3)` | `INT64` + Connect `Timestamp`, epoch 기준 밀리초 | `TIMESTAMP` |
| `timestamptz` | `STRING` + Debezium `ZonedTimestamp`, UTC 시각 문자열 | `TEXT` |

`numeric(12,2)`의 정밀도·스케일 제약과 `varchar(40)`의 길이 제약까지 적용하려면 대상 컬럼을 미리 정의한다. 소스의 스케일 제약 없는 `numeric`은 `precise`에서 `VariableScaleDecimal` 구조체로 변환되므로 위의 `Decimal` 매핑을 그대로 적용할 수 없다. [Debezium · Decimal Types](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html#postgresql-decimal-types) · [Confluent · JDBC Sink 타입 매핑](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#auto-creation-and-auto-evolution)

`timestamp`는 시간대가 없는 날짜와 시각이고, `timestamptz`는 시점을 저장하며 세션 시간대에 따라 표시된다. 실습의 `time.precision.mode=connect`는 `timestamp`를 밀리초까지 전달한다. 4~6자리 소수초가 필요한 `timestamp`에는 기본 `adaptive`의 `MicroTimestamp`와 이를 해석할 Sink 변환을 함께 검증한다. `timestamptz`를 대상에서도 시간 타입으로 저장할 경우, 대상 타입을 선언하고 UTC 문자열을 해당 타입으로 바인딩하는 경로를 검증한다. [PostgreSQL · Date/Time Types](https://www.postgresql.org/docs/17/datatype-datetime.html) · [Debezium · Temporal Types](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html#postgresql-temporal-types)
