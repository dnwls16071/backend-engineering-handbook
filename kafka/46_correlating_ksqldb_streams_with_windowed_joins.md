# Correlating ksqlDB Streams with Windowed Joins

주문 스트림과 배송 스트림을 주문 ID로 조인하면 두 시스템에서 발행한 이벤트를 연결할 수 있다. `WITHIN`으로 주문마다 배송을 찾을 시각 범위를 정하고, `GRACE PERIOD`로 순서가 뒤바뀐 이벤트를 얼마 동안 처리할지 정한다. [Confluent · Stream-Stream Joins](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#stream-stream-joins)

## 1. 매칭 범위와 지연 허용 기간

| 조인 조건 | 왼쪽 이벤트 시각이 `t`일 때 오른쪽 이벤트의 범위 |
| --- | --- |
| `WITHIN 30 SECONDS` | `t - 30초`부터 `t + 30초`까지 |
| `WITHIN (5 SECONDS, 30 SECONDS)` | `t - 5초`부터 `t + 30초`까지 |

`WITHIN`은 양쪽 이벤트의 `ROWTIME`을 비교한다. 비대칭 구문의 첫 값은 왼쪽 이벤트 이전, 둘째 값은 이후를 허용하는 범위다. 두 경계를 포함한다. `GRACE PERIOD`는 이 시간 조건을 충족하는 이벤트가 늦게 처리될 때 사용할 여유 시간이다. `WITHIN` 밖의 이벤트까지 매칭 범위가 늘어나지는 않는다. ksqlDB는 양쪽에서 지금까지 받은 이벤트를 윈도우 상태 저장소에 보관하며, 이벤트가 들어올 때 상대편 윈도우에서 찾은 각 행과 짝짓는다. [Confluent · CREATE STREAM AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream-as-select.html) · [Apache Kafka · JoinWindows](https://kafka.apache.org/39/javadoc/org/apache/kafka/streams/kstream/JoinWindows.html)

## 2. 주문 하나와 여러 배송 매칭하기

39번의 로컬 클러스터에서 두 입력 스트림을 만든다. 양쪽 모두 문자열 `order_id`가 Kafka 키이고 토픽은 한 파티션을 쓴다. 각 스트림의 `TIMESTAMP`를 값의 `event_ts`에 맞춰, 발행 시각과 별도로 주문 및 배송의 이벤트 시각을 제어한다. [39번 로컬 실습 환경](39_understanding_ksqldb_architecture_and_parallelism.md) · [Confluent · Partition Data](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/partition-data.html)

```sql
SET 'auto.offset.reset' = 'earliest';

CREATE STREAM order_events_46 (
  order_id VARCHAR KEY,
  event_ts BIGINT
) WITH (KAFKA_TOPIC = 'ksql.order-events-46.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON', PARTITIONS = 1,
        TIMESTAMP = 'event_ts');

CREATE STREAM shipment_events_46 (
  order_id VARCHAR KEY,
  shipment_id VARCHAR,
  event_ts BIGINT
) WITH (KAFKA_TOPIC = 'ksql.shipment-events-46.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON', PARTITIONS = 1,
        TIMESTAMP = 'event_ts');

CREATE STREAM order_shipments_46
  WITH (KAFKA_TOPIC = 'ksql.order-shipments-46.v1', VALUE_FORMAT = 'JSON') AS
SELECT o.order_id AS order_id, s.shipment_id AS shipment_id,
       o.ROWTIME AS order_event_ms, s.ROWTIME AS shipment_event_ms
FROM order_events_46 o
LEFT JOIN shipment_events_46 s
  WITHIN (5 SECONDS, 30 SECONDS) GRACE PERIOD 10 SECONDS
  ON o.order_id = s.order_id
EMIT CHANGES;

INSERT INTO order_events_46 VALUES ('o-46-1', 1735689610000);
INSERT INTO order_events_46 VALUES ('o-46-2', 1735689615000);
INSERT INTO shipment_events_46 VALUES ('o-46-1', 's-46-1', 1735689630000);
INSERT INTO shipment_events_46 VALUES ('o-46-1', 's-46-2', 1735689608000);

SELECT order_id, shipment_id, order_event_ms, shipment_event_ms, ROWTIME
FROM order_shipments_46 EMIT CHANGES LIMIT 2;
```

첫 주문의 시각은 `00:00:10` UTC이고 배송 매칭 범위는 `00:00:05`부터 `00:00:40`까지다. `s-46-2`의 시각인 `00:00:08`은 먼저 발행한 `s-46-1`의 `00:00:30`보다 앞선다. 두 배송 모두 같은 주문 ID의 매칭 범위 안에 있으므로 두 행이 생긴다. 아래 시각은 결과의 밀리초 값을 UTC로 바꿔 적었다. [Confluent · Stream-Stream Join Semantics](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#semantics-of-stream-stream-joins)

| 주문 ID | 배송 ID | 주문 시각 UTC | 배송 시각 UTC | 결과 `ROWTIME` UTC |
| --- | --- | --- | --- | --- |
| o-46-1 | s-46-1 | 00:00:10 | 00:00:30 | 00:00:30 |
| o-46-1 | s-46-2 | 00:00:10 | 00:00:08 | 00:00:10 |

## 3. 미매칭 주문이 나오는 시점 확인하기

두 행을 확인한 뒤 아래 배송을 추가한다. `s-46-outside`는 첫 주문과 키가 같지만 허용 범위를 초과한다. 마지막 배송은 다른 주문 ID로 스트림 시간을 `00:01:05`까지 진행시킨다. 두 번째 주문 `o-46-2`에 대한 매칭 범위의 끝은 `00:00:45`이고 지연 허용 기간의 끝은 `00:00:55`다.

```sql
INSERT INTO shipment_events_46 VALUES ('o-46-1', 's-46-outside', 1735689645000);
INSERT INTO shipment_events_46 VALUES ('clock-46', 's-46-clock', 1735689665000);

SELECT order_id, shipment_id, order_event_ms, shipment_event_ms, ROWTIME
FROM order_shipments_46 EMIT CHANGES LIMIT 3;
```

앞의 두 행에 더해 `o-46-2`가 한 행 나온다. 이 행의 `shipment_id`와 `shipment_event_ms`는 `NULL`이다. `LEFT JOIN`에서 `GRACE PERIOD`를 명시하면 스트림 시간이 매칭 범위와 지연 허용 기간을 지날 때까지 미매칭 결과를 보류한다. 입력이 멈추면 스트림 시간도 멈춰 발행이 지연될 수 있다. `GRACE PERIOD`를 생략하는 기존 동작에서는 미매칭 행이 먼저 나오고 이후 같은 주문의 매칭 행도 나올 수 있다. [Confluent · Stream-Stream Join Semantics](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/joins/join-streams-and-tables.html#semantics-of-stream-stream-joins) · [Confluent · Upgrade Notes](https://docs.confluent.io/platform/7.9/ksqldb/upgrading.html)

## 4. 조인 결과의 `ROWTIME`

양쪽이 매칭된 스트림 조인의 결과 시각은 `max(왼쪽 ROWTIME, 오른쪽 ROWTIME)`이다. 예제에서 `s-46-2`가 붙은 행의 결과 시각은 주문 시각인 `00:00:10`이다. 미매칭 행은 존재하는 입력의 시각을 쓴다. 이후 결과 스트림을 다른 윈도우 조인에 사용하면 결과 `ROWTIME`이 다음 매칭의 기준이 된다. 원래 주문과 배송 시각을 별도로 써야 하므로 예제는 양쪽 `ROWTIME`을 값 컬럼으로도 저장한다. [Confluent · Timestamps for Aggregations and Joins](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#timestamps-for-aggregations-and-joins) · [Confluent · N-Way Joins](https://docs.confluent.io/platform/current/ksqldb/developer-guide/joins/join-streams-and-tables.html#n-way-joins)
