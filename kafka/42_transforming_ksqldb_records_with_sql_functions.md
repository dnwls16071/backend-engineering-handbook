# Transforming ksqlDB Records with SQL Functions

주문 이벤트의 출력 컬럼을 고르고, 금액과 상태 조건으로 레코드를 거른다. 문자열과 시간을 화면용으로 변환한 뒤, 고객별로 주문 이벤트 수와 상품 종류 수를 계산한다. 40번의 `orders_raw`와 이벤트 네 건을 사용한다. [40번 주문 스트림](40_creating_and_querying_ksqldb_streams.md#2-주문-스트림과-실습-데이터-만들기) · [Confluent · Scalar Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html)

## 1. Projection, filter, limit

`SELECT`는 출력 열과 별칭을 지정하고, `WHERE`는 조건이 참인 이벤트만 남긴다. `LIMIT 1`은 필터를 통과한 한 행을 받은 뒤 push 쿼리를 끝낸다. 아래 조건에는 `o-101`의 `PAID` 이벤트 한 건이 일치한다. [Confluent · SELECT Push Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-push-query.html)

```sql
SET 'auto.offset.reset'='earliest';

SELECT order_id, amount AS paid_amount
FROM orders_raw
WHERE status = 'PAID' AND amount >= 100.00
EMIT CHANGES LIMIT 1;
```

`LIMIT`은 들어오는 결과 행 수를 제한한다. 파티션이 여러 개면 관찰한 결과의 전체 순서는 입력 스케줄에 따라 달라질 수 있다. 필터를 통과한 행이 `LIMIT`보다 적으면 새 이벤트를 기다리며 `Ctrl+C`로 종료할 수 있다. `NULL` 여부는 `= NULL` 대신 `IS NULL`로 검사한다. [Confluent · SELECT Push Query](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-push-query.html) · [Confluent · Keywords and Operators](https://docs.confluent.io/platform/7.9/ksqldb/reference/sql/keywords-and-operators.html)

## 2. 문자열 조합과 빈 값 처리

`CONCAT`으로 표시 문자열을 만들고 `CAST`로 금액을 `VARCHAR`로 변환한다. 계산용 `amount`는 `DECIMAL(12, 2)`를 유지한다. `COALESCE`는 왼쪽부터 검사해 처음 만나는 `NULL`이 아닌 값을 반환하고, `CASE`는 일치한 조건에 따라 상태를 표시한다. [Confluent · Scalar Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html) · [Confluent · CASE](https://docs.confluent.io/platform/7.9/ksqldb/reference/sql/keywords-and-operators.html)

```sql
SELECT order_id,
       CONCAT(order_id, ' / ', CAST(amount AS VARCHAR)) AS order_label,
       COALESCE(status, 'UNKNOWN') AS status_label,
       CASE
         WHEN status = 'PAID' THEN 'COMPLETE'
         WHEN status IS NULL THEN 'MISSING'
         ELSE 'PENDING'
       END AS lifecycle
FROM orders_raw
WHERE order_id = 'o-102'
EMIT CHANGES LIMIT 1;
```

결과는 `o-102 | o-102 / 45.50 | UNKNOWN | MISSING`이다. 빈 문자열까지 기본값으로 바꾸려면 `CASE WHEN status IS NULL OR status = '' THEN 'UNKNOWN' ELSE status END`로 조건을 지정한다.

## 3. 날짜, 시각, 타임스탬프

`DATE`는 달력 날짜, `TIME`은 하루 중 시각, `TIMESTAMP`는 밀리초 정밀도의 날짜와 시각을 나타낸다. `event_ts`와 `ROWTIME`은 epoch 밀리초를 담은 `BIGINT`다. `FROM_UNIXTIME`은 `BIGINT`를 `TIMESTAMP`로 바꾸며, `UNIX_TIMESTAMP(timestamp)`는 epoch 밀리초를 반환한다. `PARSE_DATE`와 `PARSE_TIME`은 문자열을 각각의 타입으로 변환한다. [Confluent · Data Types](https://docs.confluent.io/platform/current/ksqldb/reference/sql/data-types.html) · [Confluent · Scalar Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html)

```sql
SELECT order_id,
       FORMAT_TIMESTAMP(FROM_UNIXTIME(event_ts), 'yyyy-MM-dd HH:mm:ss', 'UTC') AS utc_time,
       FORMAT_TIMESTAMP(FROM_UNIXTIME(event_ts), 'yyyy-MM-dd HH:mm:ss', 'Asia/Seoul') AS seoul_time,
       UNIX_TIMESTAMP(PARSE_TIMESTAMP('2025-01-01 09:00:00',
                                      'yyyy-MM-dd HH:mm:ss', 'Asia/Seoul')) AS parsed_epoch_ms,
       FORMAT_DATE(PARSE_DATE('2025-01-01', 'yyyy-MM-dd'), 'yyyy/MM/dd') AS order_day,
       FORMAT_TIME(PARSE_TIME('09:00:00.000', 'HH:mm:ss.SSS'), 'HH:mm') AS order_clock
FROM orders_raw
WHERE order_id = 'o-101' AND status = 'CREATED'
EMIT CHANGES LIMIT 1;
```

| 출력 컬럼 | 결과 |
| --- | --- |
| `utc_time` | `2025-01-01 00:00:00` |
| `seoul_time` | `2025-01-01 09:00:00` |
| `parsed_epoch_ms` | `1735689600000` |
| `order_day` | `2025/01/01` |
| `order_clock` | `09:00` |

`FORMAT_TIMESTAMP`의 시간대는 같은 순간을 표시할 현지 시각을 정한다. `PARSE_TIMESTAMP`의 시간대는 입력 문자열을 어느 지역의 현지 시각으로 읽을지 정한다. epoch 초를 받는 필드는 `CAST(초_컬럼 AS BIGINT) * 1000`으로 밀리초로 바꾼다. 기존 쿼리의 `TIMESTAMPTOSTRING`과 `STRINGTOTIMESTAMP`는 각각 `FORMAT_TIMESTAMP(FROM_UNIXTIME(...))`, `UNIX_TIMESTAMP(PARSE_TIMESTAMP(...))`에 해당한다. [Confluent · Scalar Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html)

## 4. COUNT와 COUNT_DISTINCT

`COUNT(*)`는 이벤트 수를 계산한다. `COUNT(status)`는 상태 값이 있는 이벤트만 센다. `COUNT_DISTINCT(product_id)`는 스트림에서 그룹별 상품 종류 수를 HyperLogLog로 추정한다. 아래 쿼리는 입력을 고객별로 모아 지속적으로 값을 갱신한다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html) · [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html)

```sql
SET 'auto.offset.reset'='earliest';

CREATE TABLE customer_order_metrics42 WITH (
    KAFKA_TOPIC='ksql.orders.customer-metrics42.v1', KEY_FORMAT='KAFKA', VALUE_FORMAT='JSON'
) AS
SELECT customer_id,
       COUNT(*) AS event_count,
       COUNT(status) AS status_count,
       COUNT_DISTINCT(product_id) AS approx_products
FROM orders_raw
GROUP BY customer_id
EMIT CHANGES;

SELECT customer_id, event_count, status_count, approx_products
FROM customer_order_metrics42
WHERE customer_id = 'c-1';
```

네 건을 처리한 뒤 `c-1`은 `3 | 2 | 2`가 나온다. `o-101`의 두 이벤트는 전체 건수와 상태 건수에 각각 포함되고, 두 이벤트의 공통 상품 `p-1`은 상품 종류 수에 한 번 기여한다. `o-102`의 `NULL` 상태는 상태 건수에서 빠진다. 집계는 비동기로 진행되므로 예상 결과가 보일 때까지 pull 쿼리를 다시 실행한다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html) · [Confluent · Materialized Views](https://docs.confluent.io/platform/current/ksqldb/concepts/materialized-views.html)
