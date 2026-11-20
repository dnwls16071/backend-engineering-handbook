# Joining ksqlDB Streams and Tables

ksqlDB에서 주문에 고객 등급을 붙일 때는 스트림에서 테이블을 조회한다. 주문과 배송처럼 두 이벤트를 연결할 때는 두 스트림의 키와 이벤트 시각을 비교한다. 고객별 청구 설정과 등급처럼 양쪽의 현재 값을 계속 유지해야 하면 테이블 두 개를 조인한다. [Confluent · Join Streams and Tables](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html)

## 1. 입력에 따른 조인 종류

| 왼쪽과 오른쪽 입력 | 결과 | 시간 조건 | INNER | LEFT | RIGHT | FULL |
| --- | --- | --- | --- | --- | --- | --- |
| 스트림과 스트림 | 스트림 | `WITHIN` 필수 | 지원 | 지원 | 지원 | 지원 |
| 스트림과 테이블 | 스트림 | 윈도우 없음 | 지원 | 지원 | 미지원 | 미지원 |
| 테이블과 테이블, 기본 키 조인 | 테이블 | 윈도우 없음 | 지원 | 지원 | 지원 | 지원 |
| 테이블과 테이블, 외래 키 조인 | 테이블 | 윈도우 없음 | 지원 | 지원 | 미지원 | 미지원 |

조인 조건은 한 쌍의 값에 대한 등가 비교다. `INNER`는 매칭된 쌍을 반환하고, `LEFT`와 `RIGHT`는 각각 왼쪽과 오른쪽의 매칭되지 않은 행도 포함한다. `FULL`은 양쪽의 미매칭 행을 포함한다. 미매칭 행의 상대 쪽 컬럼은 `NULL`이다. `FULL` 결과에서 한쪽 키가 비어 있을 수 있어 ksqlDB는 두 키 중 값이 있는 쪽으로 결과 키를 만든다. 지속 조인 쿼리를 작성할 때는 이 합성 키를 `SELECT *`로 포함하거나 명시적으로 선택한다. [Confluent · Join Capabilities](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#join-capabilities) · [Confluent · Synthetic Keys](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/synthetic-keys.html)

스트림끼리 조인하면 새 이벤트가 들어온 쪽과 시간 범위에 있는 상대 이벤트를 모두 짝짓는다. 양쪽의 도착 순서가 이벤트 시각과 달라도, 조인 시간 범위 안에 있고 지연 허용 기간이 남아 있는 이벤트끼리는 매칭될 수 있다. 같은 주문에 배송 이벤트가 두 건이면 결과도 두 건이 될 수 있다. [46번 주문과 배송의 윈도우 조인](46_correlating_ksqldb_streams_with_windowed_joins.md) · [Confluent · Stream-Stream Joins](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#stream-stream-joins)

## 2. 스트림과 테이블 조인으로 주문 보강하기

아래 SQL은 40번의 파티션 3개짜리 `orders_raw`를 사용한다. 주문의 Kafka 키는 `order_id`이고 조인에 쓰는 `customer_id`는 값 컬럼이다. ksqlDB는 왼쪽 입력을 고객 ID 기준으로 재파티셔닝하여 오른쪽 테이블의 기본 키와 맞춘다. [40번 주문 스트림](40_creating_and_querying_ksqldb_streams.md) · [Confluent · Partition Data](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html)

```sql
SET 'auto.offset.reset' = 'earliest';

CREATE TABLE customer_tiers_44 (
  customer_id VARCHAR PRIMARY KEY,
  tier VARCHAR
) WITH (KAFKA_TOPIC = 'ksql.customer-tiers-44.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON', PARTITIONS = 3);

CREATE STREAM orders_with_tier_44
  WITH (KAFKA_TOPIC = 'ksql.orders-with-tier-44.v1', VALUE_FORMAT = 'JSON') AS
SELECT o.customer_id AS customer_id, o.order_id AS order_id,
       o.amount AS amount, t.tier AS tier
FROM orders_raw o
LEFT JOIN customer_tiers_44 t ON o.customer_id = t.customer_id
WHERE o.customer_id = 'c-44'
EMIT CHANGES;

INSERT INTO orders_raw VALUES ('o-44-1', 'c-44', 'p-44', 10.00, 1735689601000, 'PAID');

SELECT order_id, tier FROM orders_with_tier_44 EMIT CHANGES LIMIT 1;
```

첫 결과는 `o-44-1 | NULL`이다. 이 결과를 확인한 다음 고객 등급을 입력한다. 조인 쿼리가 등급 레코드를 읽을 시간을 준 뒤 두 번째 주문을 발행한다. [Confluent · Stream-Table Joins](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#stream-table-joins)

```sql
INSERT INTO customer_tiers_44 VALUES ('c-44', 'GOLD');
```

```sql
INSERT INTO orders_raw VALUES ('o-44-2', 'c-44', 'p-44', 15.00, 1735689602000, 'PAID');

SELECT order_id, tier FROM orders_with_tier_44 EMIT CHANGES LIMIT 2;
```

| `ORDER_ID` | `TIER` |
| --- | --- |
| o-44-1 | NULL |
| o-44-2 | GOLD |

테이블 레코드는 조인에서 사용할 고객 상태를 갱신한다. 출력은 새 주문이 들어올 때 만들어지므로, 고객 등급을 추가해도 첫 주문을 다시 보강하지 않는다. `INNER JOIN`이면 처음처럼 고객 상태가 비어 있을 때 해당 주문의 결과가 생기지 않는다. 조인의 양쪽 입력을 처리할 때 이벤트 시각 순서는 최선 노력으로 맞추므로, 기존 고객 상태를 사용하려면 주문 발행 전에 조인 쿼리가 고객 데이터를 먼저 처리할 시간을 확보한다. [Confluent · Stream-Table Join Semantics](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#semantics-of-stream-table-joins)

## 3. 테이블 조인으로 현재 상태 유지하기

기본 키 조인은 두 테이블에서 같은 키의 현재 행을 연결한다. 외래 키 조인은 왼쪽 테이블의 값 컬럼과 오른쪽 테이블의 기본 키를 연결한다. 아래 예제에서 하나의 고객은 여러 청구 설정을 가질 수 있다. 출력 테이블의 키는 왼쪽 입력의 `billing_id`다. 양쪽의 변경이 결과 갱신을 유발하며 입력 처리 순서에 따라 중간 상태가 보일 수 있다. [Confluent · Table-Table Joins](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#table-table-joins)

```sql
CREATE TABLE billing_profiles_44 (
  billing_id VARCHAR PRIMARY KEY,
  customer_id VARCHAR,
  channel VARCHAR
) WITH (KAFKA_TOPIC = 'ksql.billing-profiles-44.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON', PARTITIONS = 2);

CREATE TABLE billing_with_tier_44
  WITH (KAFKA_TOPIC = 'ksql.billing-with-tier-44.v1', VALUE_FORMAT = 'JSON') AS
SELECT b.billing_id AS billing_id, b.customer_id AS customer_id,
       b.channel AS channel, t.tier AS tier
FROM billing_profiles_44 b
LEFT JOIN customer_tiers_44 t ON b.customer_id = t.customer_id
EMIT CHANGES;

INSERT INTO billing_profiles_44 VALUES ('bill-44-1', 'c-44', 'EMAIL');

SELECT billing_id, channel, tier
FROM billing_with_tier_44
WHERE billing_id = 'bill-44-1';
```

두 테이블의 레코드가 반영되면 결과는 `bill-44-1 | EMAIL | GOLD`다. `INSERT INTO customer_tiers_44 VALUES ('c-44', 'SILVER');`를 실행하면 새 청구 설정을 넣지 않아도 같은 pull 쿼리에서 `SILVER`가 조회된다. [Confluent · Foreign-Key Table-Table Joins](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#semantics-of-foreign-key-table-table-joins)

## 4. 코파티셔닝과 조인 키 확인하기

코파티셔닝은 같은 조인 키의 레코드가 양쪽에서 같은 스트림 작업에 도착하도록 하는 조건이다. 두 입력의 조인 키 SQL 타입, 파티션 수, 파티셔닝 전략이 일치해야 한다. Kafka 키의 직렬화 바이트가 달라지면 같은 식별자도 다른 파티션으로 갈 수 있다. ksqlDB가 파티션 수의 불일치는 감지할 수 있으므로 키 타입과 파티션 수를 먼저 비교하고, 토픽을 쓴 프로듀서의 직렬화 및 파티셔너 설정도 확인한다. `billing_profiles_44`와 `customer_tiers_44`는 파티션 수가 다르지만 외래 키 테이블 조인에 해당해 이 조건을 요구하지 않는다. [Confluent · Co-Partitioning Requirements](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html#co-partitioning-requirements)

스트림 쪽이 `INT`, 테이블의 기본 키가 `BIGINT`라면 `ON CAST(s.customer_id AS BIGINT) = t.customer_id`로 스트림 쪽을 변환할 수 있다. 같은 스트림을 여러 조인에서 써야 한다면 CSAS에서 `PARTITION BY`와 `PARTITIONS`를 지정해 원하는 키와 파티션 수로 만든 뒤 재사용할 수 있다. 스트림-테이블에서 오른쪽 테이블을 값 컬럼으로 조회해야 하는 경우에는 그 컬럼을 Kafka 키로 쓰는 조회용 테이블을 먼저 준비한다. 그 키에 대해 여러 행이 있을 때는 어떤 값을 유지할지 함께 정의한다. [Confluent · Partition Data](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html)
