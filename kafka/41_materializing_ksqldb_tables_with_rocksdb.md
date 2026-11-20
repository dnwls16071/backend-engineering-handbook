# Materializing ksqlDB Tables with RocksDB

물질화 테이블은 Kafka를 읽으면서 기본 키별 현재 상태를 로컬 RocksDB에 갱신한다. Pull 쿼리는 이미 계산된 행을 조회한다. 주문 변경 로그를 그대로 물질화하는 `CREATE SOURCE TABLE`과 주문 이벤트를 집계해서 물질화하는 `CREATE TABLE AS SELECT`를 각각 실행한다. [Confluent · Materialized Views](https://docs.confluent.io/platform/current/ksqldb/concepts/materialized-views.html)

## 1. Kafka 토픽과 로컬 저장소

| SQL 정의 | 로컬 상태와 Kafka에 남는 내용 |
| --- | --- |
| `CREATE TABLE` | 토픽의 레코드를 기본 키별 변경 로그로 해석한다. 선언 자체는 pull 조회용 저장소를 실행하지 않는다. |
| `CREATE SOURCE TABLE` | 내부 쿼리가 입력 토픽의 키별 최신 행을 로컬에 물질화한다. 읽기 전용 테이블이며 입력은 외부 생산자가 쓴다. |
| `CREATE TABLE AS SELECT` | 지속 쿼리가 집계나 조인의 로컬 상태를 갱신하고, 결과 변경을 출력 토픽에 발행한다. 상태 복구에 쓰는 Kafka Streams 내부 changelog도 생성될 수 있다. |

RocksDB의 상태는 담당 태스크에 나뉘어 있다. `ksql.streams.state.dir`의 기본값은 `/tmp/kafka-streams`다. 운영에서는 서버별로 쓰기 가능한 영속 경로를 지정한다. 같은 시스템에서 실행되는 서버마다 경로가 고유해야 한다. 로컬 상태를 사용할 수 없거나 태스크가 다른 서버로 이동하면, Kafka Streams는 소스 또는 해당 저장소의 changelog에서 상태를 복원한다. 복구 중에는 pull 조회가 잠시 실패하거나 최신 변경이 아직 반영되지 않을 수 있다. [Confluent · CREATE TABLE](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table.html#source-tables) · [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html#ksql-streams-state-dir) · [Confluent · Kafka Streams Processor API](https://docs.confluent.io/platform/7.9/streams/developer-guide/processor-api.html)

## 2. 소스 테이블 갱신과 삭제

39번의 Kafka 네트워크에서 실습용 압축 토픽을 만든다. 아래 셸 블록은 기존 Kafka에 CLI로 연결한다. `KSQL_LAB_NETWORK`나 `KSQL_LAB_BOOTSTRAP`을 바꾼 경우 이 셸에서도 같은 값을 사용한다. [39번 서버와 CLI 구성](39_understanding_ksqldb_architecture_and_parallelism.md#3-기존-kafka에-서버와-cli-연결) · [Confluent · Log Compaction](https://docs.confluent.io/kafka/design/log_compaction.html)

```bash
kafka_ksql() {
  local tool="$1"
  shift
  docker run --rm -i --network "${KSQL_LAB_NETWORK:-kafka-lab_default}" \
    --entrypoint "$tool" confluentinc/cp-kafka:7.9.11 \
    --bootstrap-server "${KSQL_LAB_BOOTSTRAP:-kafka:29092}" "$@"
}

kafka_ksql kafka-topics --create --topic ksql.orders.status41.v1 \
  --partitions 1 --replication-factor 1 --config cleanup.policy=compact

produce_status() {
  kafka_ksql kafka-console-producer --topic ksql.orders.status41.v1 --sync \
    --property parse.key=true --property key.separator='|' \
    --property null.marker=__TOMBSTONE__
}
```

ksqlDB CLI에서 토픽을 등록한다. 기본 키가 문자열 한 개이므로 `KEY_FORMAT='KAFKA'`를 사용한다. 이 예제의 `event_ts`는 주문 페이로드에 들어 있는 업무 시간이다. [Confluent · CREATE TABLE](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table.html)

```sql
SET 'auto.offset.reset'='earliest';

CREATE SOURCE TABLE order_latest_source41 (
    order_id VARCHAR PRIMARY KEY,
    status VARCHAR,
    event_ts BIGINT
) WITH (KAFKA_TOPIC='ksql.orders.status41.v1', KEY_FORMAT='KAFKA', VALUE_FORMAT='JSON');

SELECT order_id, status, event_ts FROM order_latest_source41 WHERE order_id = 'o-201';
```

같은 셸에서 아래 세 줄을 하나씩 실행한다. 매번 다음 줄을 쓰기 전에 CLI에서 위 pull 쿼리를 다시 실행해 반영을 확인한다. 생산과 상태 갱신은 비동기다. [Confluent · SELECT Pull Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html) · [Apache Kafka 3.9 · Console Producer](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/199527475/KIP-810%2BAllow%2Bproducing%2Brecords%2Bwith%2Bnull%2Bvalues%2Bin%2BKafka%2BConsole%2BProducer)

```bash
printf '%s\n' 'o-201|{"status":"CREATED","event_ts":1735689601000}' | produce_status
printf '%s\n' 'o-201|{"status":"PAID","event_ts":1735689600000}' | produce_status
printf '%s\n' 'o-201|__TOMBSTONE__' | produce_status
```

결과는 `CREATED` 한 행, `PAID` 한 행, 빈 결과 순이다. `PAID`의 페이로드 시간이 앞서지만 같은 키로 더 높은 Kafka 오프셋에 기록된다. `__TOMBSTONE__`은 콘솔 생산자가 레코드 값 전체를 Kafka `null`로 바꾸는 표식이다. `{"status":null}`은 `status` 필드가 비어 있는 행을 만들며, `INSERT ... VALUES`에서 컬럼에 `NULL`을 지정해도 값 전체를 tombstone으로 만들 수 없다. [Confluent · CREATE TABLE](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table.html#primary-key) · [Confluent · INSERT VALUES](https://docs.confluent.io/platform/current/ksqldb/developer-guide/ksqldb-reference/insert-values.html)

## 3. 복합 기본 키로 집계 조회

40번의 주문 스트림과 이벤트 네 건을 사용한다. 이 집계에서는 `(customer_id, product_id)`가 결과 테이블의 복합 기본 키다. `KEY_FORMAT='JSON'`은 키의 두 컬럼을 모두 인코딩한다. 주문 ID로 파티션된 입력을 고객과 상품으로 집계하므로 Kafka Streams가 집계 키로 재분배한다. [40번 주문 스트림](40_creating_and_querying_ksqldb_streams.md#2-주문-스트림과-실습-데이터-만들기) · [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/current/ksqldb/reference/serialization.html)

```sql
SET 'auto.offset.reset'='earliest';

CREATE TABLE order_activity41 WITH (
    KAFKA_TOPIC='ksql.orders.activity41.v1', KEY_FORMAT='JSON', VALUE_FORMAT='JSON'
) AS
SELECT customer_id, product_id,
       COUNT(*) AS event_count,
       LATEST_BY_OFFSET(status) AS latest_status
FROM orders_raw
GROUP BY customer_id, product_id
EMIT CHANGES;

DESCRIBE order_activity41;

SELECT customer_id, product_id, event_count, latest_status
FROM order_activity41
WHERE customer_id = 'c-1' AND product_id = 'p-1';
```

처리 완료 후 `c-1 | p-1 | 2 | PAID`가 표시된다. 전체 기본 키를 등호로 지정하면 키 조회로 처리할 수 있다. `LATEST_BY_OFFSET(status)`는 집계가 읽는 파티션의 오프셋 순서로 값을 선택하며 기본적으로 `NULL` 필드를 건너뛴다. `LATEST_BY_OFFSET(status, false)`는 `NULL` 필드도 최신 값 후보에 포함한다. 소스 테이블의 키 삭제는 위에서 보낸 tombstone으로 관찰한다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html#latest-by-offset) · [Confluent · SELECT Pull Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html)

39번 Compose의 기본 저장 경로를 쓰고 있다면 쿼리가 상태를 만든 뒤 서버에서 태스크 디렉터리를 확인할 수 있다. [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html#ksql-streams-state-dir)

```bash
docker compose -f compose.ksqldb.yaml exec -T ksqldb find /tmp/kafka-streams -maxdepth 4 -type d
```
