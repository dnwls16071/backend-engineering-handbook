# Analyzing Orders and Clickstreams with ksqlDB

신발 쇼핑몰의 주문과 페이지 클릭을 ksqlDB로 집계한다. 주문과 클릭은 각각 발생한 사실을 쌓는 스트림이다. 고객 프로필, 상품 가격처럼 같은 키의 현재 값이 필요한 데이터에는 테이블을 쓴다. 이 예제의 주문에는 결제 시점의 브랜드와 고객 지역이 포함되어 있고, 클릭에는 당시 표시한 가격과 세션 ID가 포함되어 있다. [Confluent · Stream/Table Duality](https://docs.confluent.io/platform/current/ksqldb/concepts/materialized-views.html#stream-table-duality)

## 1. 입력 토픽과 테스트 이벤트 만들기

[39번 ksqlDB 환경](39_understanding_ksqldb_architecture_and_parallelism.md)의 CLI에서 아래 SQL을 실행한다. 이 실습의 주문에는 주문 한 건당 상태 이벤트 하나가 들어오며, `PAID`만 매출에 포함한다. 실제 토픽이 여러 상태 변경을 담으면 결제 이벤트의 고유 식별자로 중복을 제어하거나 주문별 최신 상태 테이블에서 집계한다. 금액은 센트 단위 정수로 저장하고, `event_ts`는 UTC epoch 밀리초로 적는다. [Confluent · CREATE STREAM](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-stream.html)

```sql
CREATE STREAM shop_orders (
    order_id VARCHAR KEY,
    customer_id VARCHAR,
    state_code VARCHAR,
    brand VARCHAR,
    amount_cents BIGINT,
    status VARCHAR,
    event_ts BIGINT
) WITH (
    KAFKA_TOPIC='ksql.shop.orders.v1', PARTITIONS=1, REPLICAS=1,
    KEY_FORMAT='KAFKA', VALUE_FORMAT='JSON', TIMESTAMP='event_ts'
);

CREATE STREAM shop_clicks (
    site_id VARCHAR,
    brand VARCHAR,
    page_name VARCHAR,
    session_id VARCHAR,
    price_cents BIGINT,
    event_ts BIGINT
) WITH (
    KAFKA_TOPIC='ksql.shop.click_events.v1', PARTITIONS=1, REPLICAS=1,
    VALUE_FORMAT='JSON', TIMESTAMP='event_ts'
);

INSERT INTO shop_orders VALUES ('o-1', 'c-101', 'CA', 'stride', 12000, 'PAID', 1795132860000);
INSERT INTO shop_orders VALUES ('o-2', 'c-101', 'CA', 'orbit',   4500, 'PAID', 1795133040000);
INSERT INTO shop_orders VALUES ('o-3', 'c-202', 'NY', 'stride',  8500, 'PAID', 1795134720000);
INSERT INTO shop_orders VALUES ('o-4', 'c-202', 'NY', 'orbit',   3000, 'CANCELLED', 1795134900000);

INSERT INTO shop_clicks VALUES ('shoe', 'stride', 'product', 's-1', 12000, 1795132860000);
INSERT INTO shop_clicks VALUES ('shoe', 'stride', 'cart',    's-1', 12000, 1795133040000);
INSERT INTO shop_clicks VALUES ('shoe', 'orbit',  'product', 's-2',  4500, 1795134000000);
INSERT INTO shop_clicks VALUES ('shoe', 'stride', 'product', 's-3',  8500, 1795134720000);

SET 'auto.offset.reset' = 'earliest';
```

`earliest`는 사용할 커밋 오프셋이 없을 때 이미 보관 중인 입력부터 읽게 한다. `TIMESTAMP='event_ts'`는 SQL의 `ROWTIME`과 윈도우 기준을 정한다. Kafka 로그 보존은 토픽의 메시지 타임스탬프와 세그먼트 설정의 영향을 받으므로, payload의 시각을 바꿨다면 토픽의 레코드 시각도 따로 확인한다. 반복 실행은 새 실습 환경이나 새 스트림·토픽 이름을 사용한다. 같은 키의 주문을 스트림에 다시 쓰면 집계가 늘어난다. [Confluent · Custom Timestamp Column](https://docs.confluent.io/platform/7.9/ksqldb/how-to-guides/use-a-custom-timestamp-column.html) · [Apache Kafka · Topic Configuration](https://kafka.apache.org/43/configuration/topic-configs/)

큰 입력이 필요하면 [47번 Datagen 구성](47_ingesting_ksqldb_data_with_kafka_connect_and_datagen.md)에 주문용 Avro 스키마를 지정할 수 있다. 생성된 데이터에서는 입력 키와 포맷, `event_ts`의 단위, 고객·상품 식별자의 일치 여부를 먼저 확인한다. 고객 지역이나 상품 속성을 별도 테이블에서 조인하는 경우 [44번 조인 문서](44_joining_ksqldb_streams_and_tables.md)의 테이블 로딩 순서와 키 규칙을 적용한다.

## 2. 결제 건수, 매출, 고객 등급 집계하기

아래 SQL은 고객·지역별 결제 건수와 브랜드별 매출을 지속적으로 갱신한다. 브랜드별 집계의 Kafka 값에도 브랜드 이름이 들어가도록 `AS_VALUE`를 사용한다. Kafka 키의 직렬화 형식은 `KAFKA`이고, Kafka Connect에서 `StringConverter`로 읽을 수 있다. [Confluent · CREATE TABLE AS SELECT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-table-as-select.html) · [Confluent · Scalar Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/scalar-functions.html#as-value)

```sql
CREATE TABLE shop_customer_counts AS
    SELECT customer_id, COUNT(*) AS order_count
    FROM shop_orders WHERE status = 'PAID'
    GROUP BY customer_id EMIT CHANGES;

CREATE TABLE shop_state_counts AS
    SELECT state_code, COUNT(*) AS order_count
    FROM shop_orders WHERE status = 'PAID'
    GROUP BY state_code EMIT CHANGES;

CREATE TABLE shop_brand_sales
WITH (
    KAFKA_TOPIC='ksql.shop.brand_sales.v1',
    KEY_FORMAT='KAFKA', VALUE_FORMAT='JSON'
) AS
    SELECT brand, AS_VALUE(brand) AS brand_name,
           COUNT(*) AS order_count, SUM(amount_cents) AS revenue_cents
    FROM shop_orders WHERE status = 'PAID'
    GROUP BY brand EMIT CHANGES;

CREATE TABLE shop_customer_tiers AS
    SELECT customer_id,
           CASE WHEN order_count >= 2 THEN 'GOLD' ELSE 'STANDARD' END AS customer_tier
    FROM shop_customer_counts EMIT CHANGES;

CREATE TABLE shop_tier_counts WITH (KEY_FORMAT='KAFKA') AS
    SELECT customer_tier, COUNT(*) AS customer_count
    FROM shop_customer_tiers
    GROUP BY customer_tier EMIT CHANGES;

CREATE TABLE shop_coupon_candidates AS
    SELECT customer_id, customer_tier
    FROM shop_customer_tiers WHERE customer_tier = 'GOLD' EMIT CHANGES;
```

처리가 끝나면 `SELECT * FROM shop_brand_sales WHERE brand = 'stride';`의 기대값은 2건, 20,500센트다. `orbit`은 1건, 4,500센트다. 고객별로 `c-101`은 2건, `c-202`는 1건이며 지역별로 CA 2건, NY 1건이다. 등급별 최종 인원은 GOLD 1명과 STANDARD 1명이고, 쿠폰 후보에는 `c-101`이 남는다. 등급이 바뀌면 이전 그룹에서 빠지고 새 그룹에 들어간다. 쿠폰 발급은 후보 테이블을 읽는 별도 작업으로 처리하고, 발급 기록은 고객과 캠페인 키로 중복을 막는다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html)

## 3. 주문·클릭을 30분 구간으로 집계하기

30분 tumbling window는 서로 겹치지 않는다. 예제에서는 늦게 들어온 이벤트를 5분까지 허용한다. 브랜드 클릭 비율의 분모는 같은 윈도우의 전체 클릭이고, 페이지별 클릭과 브랜드별 클릭은 같은 원본에서 별도 집계한다. [Confluent · Time and Windows](https://docs.confluent.io/platform/7.9/ksqldb/concepts/time-and-windows-in-ksqldb-queries.html)

```sql
CREATE TABLE shop_orders_30m AS
    SELECT status, WINDOWSTART AS window_start,
           COUNT(*) AS order_count
    FROM shop_orders WINDOW TUMBLING (SIZE 30 MINUTES, GRACE PERIOD 5 MINUTES)
    WHERE status = 'PAID' GROUP BY status EMIT CHANGES;

CREATE TABLE shop_page_clicks_30m AS
    SELECT page_name, WINDOWSTART AS window_start, COUNT(*) AS click_count
    FROM shop_clicks WINDOW TUMBLING (SIZE 30 MINUTES, GRACE PERIOD 5 MINUTES)
    GROUP BY page_name EMIT CHANGES;

CREATE TABLE shop_brand_clicks_30m AS
    SELECT brand, WINDOWSTART AS window_start, COUNT(*) AS click_count
    FROM shop_clicks WINDOW TUMBLING (SIZE 30 MINUTES, GRACE PERIOD 5 MINUTES)
    GROUP BY brand EMIT CHANGES;

CREATE TABLE shop_all_clicks_30m AS
    SELECT site_id, WINDOWSTART AS window_start, COUNT(*) AS click_count
    FROM shop_clicks WINDOW TUMBLING (SIZE 30 MINUTES, GRACE PERIOD 5 MINUTES)
    GROUP BY site_id EMIT CHANGES;

CREATE TABLE shop_brand_top_prices AS
    SELECT brand, TOPK(price_cents, 3) AS top_prices_cents,
           COUNT_DISTINCT(session_id) AS approx_sessions
    FROM shop_clicks GROUP BY brand EMIT CHANGES;
```

| 시작 시각(UTC) | 결제 | 페이지별 클릭 | 브랜드별 클릭 | 전체 클릭 |
| --- | --- | --- | --- | --- |
| 00:00 | 2 | product 2, cart 1 | stride 2, orbit 1 | 3 |
| 00:30 | 1 | product 1 | stride 1 | 1 |

`TOPK`는 같은 가격이 여러 번 들어오면 중복을 포함한다. `stride`의 상위 가격은 `[12000, 12000, 8500]`이고, 고유 가격만 필요하면 `TOPKDISTINCT`를 사용한다. `COUNT_DISTINCT`는 세션 ID의 고유 개수 추정치다. 여기서 같은 세션의 장바구니와 상품 페이지 클릭은 두 클릭으로 세지만 한 세션으로 집계한다. [Confluent · Aggregate Functions](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/aggregate-functions.html)

`SHOW QUERIES;`와 `DESCRIBE SHOP_BRAND_SALES EXTENDED;`로 지속 쿼리와 결과 토픽을 확인한다. [50번 Elasticsearch·Kibana 문서](50_visualizing_realtime_ksqldb_analytics_with_kibana.md)는 브랜드별 최신 집계와 클릭 이벤트를 표시한다.
