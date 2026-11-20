# Creating and Querying ksqlDB Streams

`CREATE STREAM`으로 Kafka 레코드의 키와 값에 SQL 스키마를 붙인다. 같은 키의 주문 이벤트 두 건을 읽어 스트림의 행이 어떻게 생기는지 확인하고, push·pull 쿼리와 지속 쿼리의 실행 수명을 비교한다. [Confluent · Stream Processing Concepts](https://docs.confluent.io/platform/7.9/ksqldb/concepts/overview.html)

## 1. 스트림과 테이블의 키

| Kafka 레코드 | 스트림 (`KEY`) | 테이블 (`PRIMARY KEY`) |
| --- | --- | --- |
| 같은 키의 값이 두 번 도착 | 이벤트 두 건으로 보인다. | 해당 키의 행이 새 값으로 갱신된다. |
| 키가 `NULL`이고 값은 존재 | 이벤트를 읽을 수 있다. | 행으로 반영되지 않는다. |
| 값 전체가 `NULL`인 tombstone | 이벤트로 읽히지 않는다. | 같은 키의 행을 삭제한다. |

`KEY`를 선언한 컬럼은 Kafka 레코드의 키에서 읽고, 일반 컬럼은 값에서 읽는다. Kafka 값의 JSON 필드에 `order_id`가 있어도 `order_id VARCHAR KEY`는 Kafka 레코드 키를 참조한다. 키가 없는 스트림의 스키마에는 `KEY`를 생략하고 `KEY_FORMAT='NONE'`을 지정할 수 있다. 이후 고객별 처리가 필요하면 `PARTITION BY customer_id`를 쓰는 쿼리로 고객 키를 만든다. [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html) · [Confluent · CREATE TABLE](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table.html) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/current/ksqldb/reference/serialization.html)

## 2. 주문 스트림과 실습 데이터 만들기

39번의 ksqlDB CLI에서 실행한다. `ksql.orders.v1`이 없으면 아래 DDL이 파티션 3개, 복제 계수 1로 토픽을 생성한다. 이미 존재하는 토픽을 등록할 때는 실제 키·값의 포맷에 맞춰 선언한다. `KEY_FORMAT='KAFKA'`의 `VARCHAR`는 Kafka 문자열 직렬화 형식으로 읽고, `VALUE_FORMAT='JSON'`은 Schema Registry 없이 JSON 값에 선언한 컬럼을 매핑한다. `AVRO`, `PROTOBUF`, `JSON_SR`를 쓰려면 Schema Registry가 필요하다. [39번 서버와 CLI 구성](39_understanding_ksqldb_architecture_and_parallelism.md#3-기존-kafka에-서버와-cli-연결) · [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/current/ksqldb/reference/serialization.html)

```sql
CREATE STREAM orders_raw (
    order_id VARCHAR KEY,
    customer_id VARCHAR,
    product_id VARCHAR,
    amount DECIMAL(12, 2),
    event_ts BIGINT,
    status VARCHAR
) WITH (
    KAFKA_TOPIC='ksql.orders.v1', PARTITIONS=3, REPLICAS=1,
    KEY_FORMAT='KAFKA', VALUE_FORMAT='JSON', TIMESTAMP='event_ts'
);

DESCRIBE EXTENDED orders_raw;
```

아래 네 건은 후속 예제에서도 사용한다. 빈 `ksql.orders.v1`에 한 번 실행하면 같은 `o-101` 키에 `CREATED`, `PAID`가 순서대로 기록된다. `o-102`의 `status`는 `NULL`이지만 레코드 값에는 다른 필드가 있으므로 이벤트가 스트림에 나타난다. [Confluent · INSERT VALUES](https://docs.confluent.io/platform/current/ksqldb/developer-guide/ksqldb-reference/insert-values.html)

```sql
INSERT INTO orders_raw VALUES ('o-101', 'c-1', 'p-1', 120.00, 1735689600000, 'CREATED');
INSERT INTO orders_raw VALUES ('o-101', 'c-1', 'p-1', 120.00, 1735689601000, 'PAID');
INSERT INTO orders_raw VALUES ('o-102', 'c-1', 'p-2', 45.50, 1735689602000, NULL);
INSERT INTO orders_raw VALUES ('o-103', 'c-2', 'p-3', 85.00, 1735689603000, 'PAID');
```

`ROWTIME`은 밀리초 단위의 이벤트 시간이다. 기본값은 Kafka 레코드 타임스탬프이며, 이 스트림에서는 `TIMESTAMP='event_ts'`로 값 컬럼을 사용한다. `ROWPARTITION`과 `ROWOFFSET`은 읽은 토픽의 파티션과 오프셋이다. 숫자형 시간이 epoch 초 단위인 데이터라면 밀리초로 정규화한 값을 사용한다. [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html)

## 3. Push, pull, 지속 쿼리

이미 넣어 둔 이벤트를 읽으려면 새 쿼리를 시작하기 전에 `earliest`를 지정한다. `auto.offset.reset`은 유효한 초기 오프셋이 없을 때 적용된다. `earliest`는 현재 보존된 첫 오프셋부터 읽고, 기본 `latest`는 그때의 로그 끝부터 읽는다. 이미 유효한 오프셋으로 실행·재개하는 지속 쿼리의 위치는 이 세션 설정으로 바뀌지 않는다. 새 CLI 세션에서는 필요한 `SET`을 다시 실행한다. [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html#ksql-streams-auto-offset-reset)

```sql
SET 'auto.offset.reset'='earliest';

SELECT order_id, status, ROWTIME, ROWPARTITION, ROWOFFSET
FROM orders_raw
WHERE order_id = 'o-101'
EMIT CHANGES LIMIT 2;

SELECT order_id, status FROM orders_raw WHERE order_id = 'o-101' LIMIT 2;
```

- Push 쿼리는 `EMIT CHANGES`로 결과를 전송한다. 첫 쿼리에서는 `CREATED`와 `PAID`가 같은 파티션의 증가하는 오프셋으로 표시되고 `ROWTIME`은 각각 `1735689600000`, `1735689601000`이다. 두 행을 받은 뒤 종료된다. `LIMIT`을 생략했거나 일치 행이 두 건 미만이면 새 이벤트를 기다린다. CLI에서는 `Ctrl+C`로 구독을 끝낸다. [Confluent · SELECT Push Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-push-query.html)
- Pull 쿼리는 `EMIT CHANGES` 없이 유한한 결과를 반환한다. 두 번째 쿼리는 일반 스트림에서 일치하는 이벤트를 읽으므로 두 상태를 반환할 수 있다. 물질화 테이블에 기본 키로 조회하면 해당 키의 현재 행을 읽는다. 일반 스트림의 pull 지원은 서버의 `ksql.query.pull.stream.enabled` 설정에 따르며, `CREATE SOURCE STREAM`에는 적용되지 않는다. Pull 쿼리에서 집계나 조인이 필요하면 지속 쿼리로 테이블을 만들고 그 결과를 조회한다. [Confluent · SELECT Pull Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html) · [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html) · [Confluent · KsqlConfig](https://github.com/confluentinc/ksql/blob/master/ksqldb-common/src/main/java/io/confluent/ksql/util/KsqlConfig.java)
- `CREATE STREAM AS SELECT`와 `CREATE TABLE AS SELECT`로 시작한 지속 쿼리는 CLI가 닫혀도 실행되며 결과를 Kafka 토픽에 기록한다. `SHOW QUERIES;`에서 ID를 확인하고 `TERMINATE <query_id>;`로 실행을 중지한다. [Confluent · Query Concepts](https://docs.confluent.io/platform/current/ksqldb/concepts/queries.html) · [Confluent · Quick Reference](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/quick-reference.html)

## 4. 키가 없는 스트림에 값 컬럼 추가

`ALTER STREAM ... ADD COLUMN`으로 토픽에 직접 등록한 스트림에 값 컬럼을 더한다. `CREATE STREAM AS SELECT`로 만든 스트림의 출력 스키마는 쿼리가 정의한다. 아래에서 `channel`을 추가하기 전에 쓴 JSON 레코드에는 그 필드가 없으므로 새 스키마로 읽으면 `NULL`이다. SQL에 이미 등록된 기존 타입을 확인할 때는 `DESCRIBE`를 사용한다. `VARCHAR`, `BOOLEAN`, `INT`, `BIGINT`, `DOUBLE`, `DECIMAL(p,s)` 같은 스칼라 타입과 `ARRAY`, `MAP`, `STRUCT` 같은 복합 타입을 선언할 수 있다. [Confluent · Quick Reference](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/quick-reference.html#alter-stream) · [Confluent · Data Types](https://docs.confluent.io/platform/current/ksqldb/reference/sql/data-types.html)

```sql
CREATE STREAM orders_unkeyed40 (order_id VARCHAR, status VARCHAR)
WITH (KAFKA_TOPIC='ksql.orders.unkeyed40.v1', PARTITIONS=1, REPLICAS=1,
      KEY_FORMAT='NONE', VALUE_FORMAT='JSON');
INSERT INTO orders_unkeyed40 VALUES ('u-1', 'CREATED');

ALTER STREAM orders_unkeyed40 ADD COLUMN channel VARCHAR;
INSERT INTO orders_unkeyed40 VALUES ('u-2', 'CREATED', 'WEB');

SELECT order_id, channel FROM orders_unkeyed40 EMIT CHANGES LIMIT 2;
```

같은 CLI 세션에서 `earliest` 설정을 유지하면 `u-1 | NULL`과 `u-2 | WEB`이 순서대로 표시된다.
