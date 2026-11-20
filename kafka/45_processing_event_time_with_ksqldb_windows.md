# Processing Event Time with ksqlDB Windows

ksqlDB에서는 주문의 이벤트 시각으로 집계 구간을 정할 수 있다. 네트워크가 끊겨 몇 초 늦게 도착한 주문도 지연 허용 기간 안에 들어오면 원래 시간 구간의 집계에 반영된다. 고객별 주문 횟수를 텀블링, 호핑, 세션 윈도우로 계산한다. [Confluent · Time and Windows](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html)

## 1. 이벤트 시각과 `ROWTIME`

| 시각 | 의미 | 예시 |
| --- | --- | --- |
| 이벤트 시각 | 원천 시스템에서 사건이 발생한 시각 | 주문이 결제된 시각 |
| 수집 시각 | Kafka 브로커가 레코드를 로그에 추가한 시각 | 결제 이벤트가 Kafka에 들어온 시각 |
| 처리 시각 | 스트리밍 애플리케이션이 레코드를 처리한 시각 | ksqlDB가 지연된 주문을 읽고 집계한 시각 |

`ROWTIME`은 ksqlDB가 윈도우와 조인에 사용하는 밀리초 단위 Unix epoch 시각이다. 기본값은 Kafka 레코드의 타임스탬프다. 토픽의 `message.timestamp.type`이 `CreateTime`이면 프로듀서가 지정한 타임스탬프를 쓴다. Java 프로듀서가 타임스탬프를 생략하면 전송 시점의 시각을 쓴다. `LogAppendTime`이면 브로커가 로그에 추가하는 시각으로 타임스탬프를 덮어쓴다. [Confluent · Timestamp Assignment](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#timestamp-assignment)

`WITH (TIMESTAMP = 'event_ts')`를 지정하면 Kafka 레코드의 타임스탬프 대신 주문 값의 `event_ts`를 `ROWTIME`으로 사용한다. `BIGINT`는 Unix epoch 밀리초여야 한다. 시각이 `VARCHAR`로 들어오면 `TIMESTAMP_FORMAT`도 지정해 문자열을 파싱한다. [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html#timestamp)

## 2. 텀블링, 호핑, 세션 윈도우

| 윈도우 | SQL 예시 | 포함 방식 |
| --- | --- | --- |
| 텀블링 | `WINDOW TUMBLING (SIZE 1 MINUTE)` | 겹치지 않는 고정 구간이다. 이벤트 하나는 한 구간에 들어간다. |
| 호핑 | `WINDOW HOPPING (SIZE 1 MINUTE, ADVANCE BY 30 SECONDS)` | 30초마다 1분 길이의 구간이 시작된다. 이벤트 하나가 여러 구간에 들어갈 수 있다. |
| 세션 | `WINDOW SESSION (20 SECONDS)` | 같은 키의 이벤트 사이가 비활성 간격 이내면 같은 세션에 포함된다. 늦게 들어온 이벤트가 두 세션을 이어 붙일 수 있다. |

텀블링과 호핑은 시작 시각을 포함하고 종료 시각은 제외한다. 경계는 UTC의 Unix epoch에 맞추므로 하루 길이의 윈도우를 한국 시각의 자정부터 집계하려면 시간대 경계를 따로 고려한다. 세션의 시작과 끝은 각각 세션에 속한 가장 이른 이벤트와 가장 늦은 이벤트의 시각이고, 두 끝을 모두 포함한다. [Confluent · Window Types](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#window-types)

## 3. 고객별 주문 이벤트 집계하기

39번의 로컬 클러스터에서 아래 SQL을 실행한다. 실습 토픽은 한 파티션으로 만들고 고객 ID를 Kafka 키로 사용한다. 세 집계 쿼리가 만들고 유지하는 테이블은 고객 ID와 윈도우 경계로 행을 구분한다. `WINDOWSTART`와 `WINDOWEND`를 결과 값에도 넣어 조회에서 밀리초 경계를 확인한다. [39번 로컬 실습 환경](39_understanding_ksqldb_architecture_and_parallelism.md) · [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html)

```sql
SET 'auto.offset.reset' = 'earliest';

CREATE STREAM orders_window_45 (
  customer_id VARCHAR KEY,
  order_id VARCHAR,
  event_ts BIGINT
) WITH (KAFKA_TOPIC = 'ksql.orders-window-45.v1',
        KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON', PARTITIONS = 1,
        TIMESTAMP = 'event_ts');

CREATE TABLE order_tumbling_45 AS
SELECT customer_id, WINDOWSTART AS start_ms, WINDOWEND AS end_ms,
       COUNT(*) AS order_events
FROM orders_window_45
WINDOW TUMBLING (SIZE 1 MINUTE, RETENTION 1 HOUR, GRACE PERIOD 10 SECONDS)
GROUP BY customer_id
EMIT CHANGES;

CREATE TABLE order_hopping_45 AS
SELECT customer_id, WINDOWSTART AS start_ms, WINDOWEND AS end_ms,
       COUNT(*) AS order_events
FROM orders_window_45
WINDOW HOPPING (SIZE 1 MINUTE, ADVANCE BY 30 SECONDS,
                RETENTION 1 HOUR, GRACE PERIOD 10 SECONDS)
GROUP BY customer_id
EMIT CHANGES;

CREATE TABLE order_sessions_45 AS
SELECT customer_id, WINDOWSTART AS start_ms, WINDOWEND AS end_ms,
       COUNT(*) AS order_events
FROM orders_window_45
WINDOW SESSION (20 SECONDS, RETENTION 1 HOUR, GRACE PERIOD 10 SECONDS)
GROUP BY customer_id
EMIT CHANGES;

INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-1', 1735689605000);
INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-2', 1735689635000);
INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-3', 1735689620000);
INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-4', 1735689660000);
INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-5', 1735689675000);
```

앞의 세 이벤트 시각은 같은 날 `00:00:05`, `00:00:35`, `00:00:20` UTC다. 마지막으로 들어온 `00:00:20` 주문이 20초 안에 있는 앞의 두 이벤트를 연결하므로 세션 하나로 합쳐진다. `00:01:00`에 발생한 네 번째 주문은 첫 텀블링 윈도우의 종료 경계에 있으므로 다음 윈도우에서 집계된다. [Confluent · Session and Tumbling Windows](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#window-types)

```sql
SELECT order_id, ROWTIME, event_ts FROM orders_window_45 EMIT CHANGES LIMIT 5;

SELECT start_ms, end_ms, order_events FROM order_tumbling_45
WHERE customer_id = 'c-45' AND WINDOWSTART = 1735689600000;

SELECT start_ms, end_ms, order_events FROM order_hopping_45
WHERE customer_id = 'c-45' AND WINDOWSTART = 1735689630000;

SELECT start_ms, end_ms, order_events FROM order_sessions_45
WHERE customer_id = 'c-45';
```

입력이 모두 처리된 뒤 첫 조회에서 `ROWTIME`과 `event_ts`가 같은지 확인한다. 이어서 pull 쿼리에서는 다음 결과를 확인할 수 있다. 표의 시각은 밀리초 값을 UTC로 바꿔 적었다. [Confluent · Pull Queries on Windowed Tables](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/select-pull-query.html#window)

| 집계 | 시작 UTC | 종료 UTC | `ORDER_EVENTS` |
| --- | --- | --- | ---: |
| 텀블링 | 00:00:00 | 00:01:00 | 3 |
| 호핑 | 00:00:30 | 00:01:30 | 3 |
| 세션 | 00:00:05 | 00:00:35 | 3 |
| 세션 | 00:01:00 | 00:01:15 | 2 |

## 4. 지연 허용 기간과 결과 발행

`GRACE PERIOD`는 윈도우가 끝난 뒤 늦은 이벤트를 집계에 반영할 수 있는 기간이다. 진행 기준인 스트림 시간은 해당 처리 작업이 관측한 이벤트 시각 중 최댓값으로 전진한다. `00:01:15` 이벤트가 반영된 뒤에는 첫 텀블링 윈도우의 종료 시각 `00:01:00`과 지연 허용 기간 10초를 지난 상태다. 아래 이벤트를 발행해도 시작 시각 `00:00:00`의 텀블링 집계는 `3`이다. [Confluent · Out-of-Order Events](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#out-of-order-events)

```sql
INSERT INTO orders_window_45 VALUES ('c-45', 'o-45-late', 1735689640000);

SELECT start_ms, end_ms, order_events FROM order_tumbling_45
WHERE customer_id = 'c-45' AND WINDOWSTART = 1735689600000;
```

`EMIT CHANGES`는 갱신을 계속 발행하며 캐시와 커밋 주기가 중간 발행 빈도에 영향을 준다. 윈도우 집계에서 `EMIT FINAL`을 쓰면 윈도우가 닫힌 뒤 최종값만 발행한다. 입력이 없어서 스트림 시간이 멈추면 벽시계가 지나도 최종값 발행이 지연될 수 있다. 과거 집계 조회에 필요한 보존 기간은 `RETENTION`으로 정한다. 고정 윈도우에서는 크기, 세션 윈도우에서는 비활성 간격에 지연 허용 기간을 더한 값보다 길게 설정한다. [Confluent · Window Emission and Retention](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html#window-emission)
