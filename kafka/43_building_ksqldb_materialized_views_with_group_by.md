# Building ksqlDB Materialized Views with GROUP BY

ksqlDB에서 고객별 주문 건수와 합계를 자주 조회할 때는 `GROUP BY` 결과를 테이블로 유지할 수 있다. 주문 이벤트가 들어올 때마다 해당 고객의 집계가 갱신되고, 조회 요청은 이미 계산된 결과를 읽는다. [Confluent · Materialized Views](https://docs.confluent.io/platform/7.9/ksqldb/concepts/materialized-views.html)

## 1. 집계 결과를 테이블로 만들기

`CREATE TABLE AS SELECT`(CTAS)는 지속 쿼리를 만들고, 키별 현재 상태를 materialize하며, 변경분을 결과 Kafka 토픽에 기록한다. `CREATE STREAM AS SELECT`(CSAS)는 필터링, 컬럼 변환, 스트림 조인 등으로 생성한 결과 이벤트를 토픽에 기록한다. 예를 들어 결제된 주문 이벤트만 발행할 때는 CSAS를, 고객별 누적 결제 금액을 유지할 때는 CTAS를 사용한다. [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html) · [Confluent · CREATE STREAM AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream-as-select.html)

아래 실습은 40번에서 등록한 주문 스트림 `orders_raw`를 사용한다. 새 집계 쿼리의 `auto.offset.reset`이 기본값 `latest`이면 유효한 커밋 오프셋이 없을 때 새 레코드부터 읽는다. `earliest`는 토픽에 남아 있는 가장 오래된 오프셋에서 읽기 시작한다. 기존 쿼리가 유효한 오프셋을 커밋했다면 재시작 시 해당 위치에서 이어서 읽는다. 쿼리를 만들기 전에 설정하고, 실습 뒤에는 `UNSET 'auto.offset.reset';`으로 세션 설정을 해제할 수 있다. [40번 주문 스트림](40_creating_and_querying_ksqldb_streams.md) · [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html#ksql-streams-auto-offset-reset)

```sql
INSERT INTO orders_raw VALUES ('o-43-1', 'c-43', 'p-43-a', 12.50, 1735689602000, 'PAID');
INSERT INTO orders_raw VALUES ('o-43-1', 'c-43', 'p-43-a', 7.50, 1735689601000, 'PENDING');
INSERT INTO orders_raw VALUES ('o-43-1', 'c-43', 'p-43-b', 5.00, 1735689603000, NULL);

SET 'auto.offset.reset' = 'earliest';

CREATE TABLE customer_order_totals_43
  WITH (KAFKA_TOPIC = 'ksql.customer-order-totals-43.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON') AS
SELECT customer_id,
       COUNT(*) AS order_events,
       SUM(amount) AS total_amount,
       EARLIEST_BY_OFFSET(status) AS first_status,
       LATEST_BY_OFFSET(status) AS last_status,
       LATEST_BY_OFFSET(status, false) AS last_status_with_null
FROM orders_raw
WHERE customer_id = 'c-43'
GROUP BY customer_id
EMIT CHANGES;

SELECT customer_id, order_events, total_amount,
       first_status, last_status, last_status_with_null
FROM customer_order_totals_43
WHERE customer_id = 'c-43';
```

세 이벤트는 같은 주문 키로 발행되므로 입력 파티션 하나에서 순서를 비교할 수 있다. 이 집계는 주문 ID의 고유 개수 대신 이벤트 건수를 센다. 초기 데이터가 모두 반영된 뒤 마지막 `SELECT`를 다시 실행하면 다음 행이 나온다. Pull 쿼리는 실행 시점의 상태를 가져와 종료한다. 변경분을 계속 보려면 같은 키 조건에 `EMIT CHANGES`를 붙여 push 쿼리로 실행한다. [Confluent · Pull Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html) · [Confluent · Push Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-push-query.html)

| `CUSTOMER_ID` | `ORDER_EVENTS` | `TOTAL_AMOUNT` | `FIRST_STATUS` | `LAST_STATUS` | `LAST_STATUS_WITH_NULL` |
| --- | ---: | ---: | --- | --- | --- |
| c-43 | 3 | 25.00 | PAID | PENDING | NULL |

`EARLIEST_BY_OFFSET`과 `LATEST_BY_OFFSET`은 집계가 처리하는 파티션의 오프셋 순서를 사용한다. 위 예제에서 `PENDING`의 `event_ts`는 `PAID`보다 작지만 뒤에 발행됐다. 따라서 기본 설정의 마지막 상태는 `PENDING`이다. 두 함수는 기본적으로 `NULL`을 건너뛰며 두 번째 인자에 `false`를 주면 포함한다. 여러 파티션에서 같은 그룹으로 모인 이벤트는 재파티셔닝된 순서에 영향을 받으므로, 이벤트 시각 기준으로 마지막 상태를 고르려면 시각과 같은 시각일 때의 순서 기준도 정의해야 한다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html#latest-by-offset) · [Confluent · Partition Data](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html)

## 2. 복합 키와 `AS_VALUE`

`GROUP BY customer_id, product_id`는 두 컬럼을 테이블의 기본 키로 만든다. 그룹 컬럼을 모두 `SELECT`에 넣고 복합 키를 지원하는 `KEY_FORMAT`을 선택한다. 이 예제의 `JSON`은 복합 키를 지원하고 Schema Registry가 필요 없다. Kafka의 value만 읽는 소비자에게도 식별자를 제공하려면 `AS_VALUE`로 키 컬럼을 value에 복사한다. [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html) · [Confluent · AS_VALUE](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html#as-value)

```sql
CREATE TABLE customer_product_totals_43
  WITH (KAFKA_TOPIC = 'ksql.customer-product-totals-43.v1',
        KEY_FORMAT = 'JSON', VALUE_FORMAT = 'JSON') AS
SELECT customer_id, product_id,
       AS_VALUE(customer_id) AS customer_id_value,
       AS_VALUE(product_id) AS product_id_value,
       COUNT(*) AS order_events,
       SUM(amount) AS total_amount
FROM orders_raw
WHERE customer_id = 'c-43'
GROUP BY customer_id, product_id
EMIT CHANGES;

DESCRIBE customer_product_totals_43;

SELECT customer_id, product_id, order_events, total_amount
FROM customer_product_totals_43
WHERE customer_id = 'c-43' AND product_id = 'p-43-a';
```

기대 결과는 `c-43 | p-43-a | 2 | 20.00`이다. `DESCRIBE`에서 `CUSTOMER_ID`와 `PRODUCT_ID`가 키 컬럼인지 확인한다. `PRINT 'ksql.customer-product-totals-43.v1' FROM BEGINNING;`을 실행하면 Kafka 레코드의 key와 value를 확인할 수 있다. 기본 설정의 pull 쿼리에서는 복합 키의 모든 컬럼을 지정한다. [Confluent · Pull Query WHERE Clause](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html#where-clause-guidelines)

## 3. 재파티셔닝과 RocksDB 상태 저장소

`orders_raw`의 Kafka 키는 `order_id`다. 고객별 집계를 실행하면 ksqlDB가 `customer_id`를 새 키로 사용해 재파티셔닝한다. 같은 고객의 모든 레코드가 같은 작업에 도착해야 해당 고객의 집계를 한 곳에서 유지할 수 있기 때문이다. 여러 쿼리가 같은 재파티셔닝을 반복한다면 CSAS의 `PARTITION BY`로 고객 키 스트림을 미리 만들고 공통 입력으로 쓸 수 있다. `SHOW QUERIES;`로 쿼리 ID를 확인한 뒤 `EXPLAIN`으로 실행 계획을 확인한다. [Confluent · Partition Data](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html) · [Confluent · Performance Guidelines](https://docs.confluent.io/platform/7.9/ksqldb/operate-and-deploy/performance-guidelines.html)

집계는 기본적으로 로컬 RocksDB 상태 저장소에 현재 값을 보관한다. Kafka의 상태 변경 로그는 장애 후 상태를 복구하는 데 쓰이고, CTAS의 결과 토픽은 집계 변경분을 후속 쿼리나 소비자에게 전달한다. 토픽을 compaction하면 중간 갱신 레코드는 정리될 수 있다. [Confluent · Performance Guidelines](https://docs.confluent.io/platform/7.9/ksqldb/operate-and-deploy/performance-guidelines.html) · [Confluent · Materialized Views](https://docs.confluent.io/platform/7.9/ksqldb/concepts/materialized-views.html)
