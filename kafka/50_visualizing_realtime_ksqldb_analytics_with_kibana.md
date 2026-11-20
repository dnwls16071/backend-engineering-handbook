# Visualizing Real-Time ksqlDB Analytics with Kibana

[49번 실습](49_analyzing_orders_and_clickstreams_with_ksqldb.md)의 브랜드별 매출과 클릭 이벤트를 Kafka Connect로 Elasticsearch에 보내고 Kibana에서 조회한다. 매출은 브랜드당 문서 하나에 최신 집계를 저장한다. 클릭은 이벤트마다 문서를 하나씩 만들며, Kibana에서 클릭 시각으로 30분 구간을 나눈다. 두 인덱스는 각각 현재 집계와 과거 이벤트를 표현한다. [Confluent · Elasticsearch Sink](https://docs.confluent.io/kafka-connectors/elasticsearch/current/index.html) · [Elastic · Date Histogram](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/search-aggregations-bucket-datehistogram-aggregation.html)

## 1. Kafka 토픽을 확인하고 인덱스 매핑 만들기

[48번 Elasticsearch Sink 구성](48_indexing_ksqldb_results_in_elasticsearch.md)에서 사용한 동일한 Connect 워커와 Elasticsearch, Kibana를 사용한다. ksqlDB CLI에서 `PRINT 'ksql.shop.brand_sales.v1' FROM BEGINNING LIMIT 1;`과 `PRINT 'ksql.shop.click_events.v1' FROM BEGINNING LIMIT 1;`을 실행한다. 매출 토픽에는 브랜드 문자열 키와 `BRAND_NAME`, `ORDER_COUNT`, `REVENUE_CENTS` 값 필드가 있다. 클릭 토픽에는 키가 없고 값의 `EVENT_TS`가 UTC epoch 밀리초다. SQL에서 따옴표 없이 선언한 필드 이름은 대문자로 들어간다. [Confluent · PRINT](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/print.html) · [Confluent · ksqlDB Serialization](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html)

Sink를 등록하기 전에 새 실습 인덱스와 타입을 지정한다. `EVENT_TS`는 Elasticsearch `date` 필드로 설정하고, 문자열 범주와 세션 ID는 `keyword`로 둔다. 금액을 저장할 `long`의 단위는 센트다. 아래 호스트 주소는 48번의 로컬 실습용이다. [Elastic · Create Index API](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/indices-create-index.html) · [Elastic · Date Field](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/date.html)

```bash
es_url=http://127.0.0.1:9200
sales_topic=ksql.shop.brand_sales.v1
click_topic=ksql.shop.click_events.v1

curl -fsS -X PUT "$es_url/$sales_topic" -H 'Content-Type: application/json' -d @- <<'JSON'
{
  "mappings": {
    "properties": {
      "BRAND_NAME": { "type": "keyword" },
      "ORDER_COUNT": { "type": "long" },
      "REVENUE_CENTS": { "type": "long" }
    }
  }
}
JSON

curl -fsS -X PUT "$es_url/$click_topic" -H 'Content-Type: application/json' -d @- <<'JSON'
{
  "mappings": {
    "properties": {
      "SITE_ID": { "type": "keyword" },
      "BRAND": { "type": "keyword" },
      "PAGE_NAME": { "type": "keyword" },
      "SESSION_ID": { "type": "keyword" },
      "PRICE_CENTS": { "type": "long" },
      "EVENT_TS": { "type": "date", "format": "epoch_millis" }
    }
  }
}
JSON
```

## 2. 최신 매출과 클릭 이력에 맞춰 Sink 설정하기

매출 Sink는 `key.ignore=false`로 브랜드를 문서 ID에 사용한다. 집계 갱신마다 결과 전체를 기록하므로 `INSERT`로 기존 문서를 교체하고, 같은 키의 tombstone은 문서를 삭제한다. 클릭 Sink는 `key.ignore=true`로 토픽·파티션·오프셋에서 문서 ID를 만든다. 같은 Kafka 레코드의 재전송에는 같은 ID가 쓰이며, 원천에서 클릭을 새 오프셋으로 다시 발행하면 문서가 추가된다. `schema.ignore=true`는 앞에서 정의한 Elasticsearch 매핑을 사용한다. [Confluent · Elasticsearch Sink Configuration](https://docs.confluent.io/kafka-connectors/elasticsearch/current/configuration_options.html)

```bash
connect_url=http://127.0.0.1:18083

register_shop_sink() {
  local name="$1" topic="$2" ignore_key="$3" on_null="$4"
  jq -n --arg topic "$topic" --arg ignore "$ignore_key" --arg on_null "$on_null" '{
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "tasks.max": "1",
    "topics": $topic,
    "connection.url": "http://elasticsearch:9200",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "schema.ignore": "true",
    "write.method": "INSERT",
    "key.ignore": $ignore,
    "behavior.on.null.values": $on_null
  }' |
    curl -fsS -X PUT "$connect_url/connectors/$name/config" \
      -H 'Content-Type: application/json' --data-binary @-
}

register_shop_sink shop-brand-sales-es "$sales_topic" false DELETE
register_shop_sink shop-click-events-es "$click_topic" true IGNORE

for connector in shop-brand-sales-es shop-click-events-es; do
  curl -fsS "$connect_url/connectors/$connector/status" | jq '{name, connector, tasks}'
done
```

Connect 태스크가 `RUNNING`으로 바뀌고 인덱싱이 끝난 뒤 조회한다. 일반 검색에는 Elasticsearch의 refresh 간격만큼 지연이 있을 수 있다. 같은 브랜드로 새 결제 한 건을 보내면 집계 값은 바뀌고 매출 문서 수는 그대로 유지된다. [Elastic · Near Real-Time Search](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/near-real-time.html)

```bash
curl -fsS "$es_url/$sales_topic/_doc/stride" |
  jq -e '._source | .BRAND_NAME == "stride" and .ORDER_COUNT == 2 and .REVENUE_CENTS == 20500'

curl -fsS "$es_url/$sales_topic/_count" | jq -e '.count == 2'
curl -fsS "$es_url/$click_topic/_count" | jq -e '.count == 4'
```

## 3. Kibana에서 현재 매출과 클릭 타임라인 확인하기

Kibana `http://127.0.0.1:5601`에서 두 Data View를 생성한다. 매출 인덱스는 시간 필드를 선택하지 않고, 클릭 인덱스는 `EVENT_TS`를 시간 필드로 고른다. 실습 데이터가 보이도록 날짜 범위를 2026년 11월 20일 00:00~01:00 UTC로 설정한다. 브라우저가 한국 시간대를 쓰면 09:00~10:00에 해당한다. [Elastic · Kibana Data Views](https://www.elastic.co/guide/en/kibana/8.17/data-views.html)

| 패널 | Lens 설정 | 기대값 |
| --- | --- | --- |
| 브랜드별 결제 건수 | `BRAND_NAME`별 `Sum(ORDER_COUNT)` | stride 2, orbit 1 |
| 브랜드별 매출 | `BRAND_NAME`별 `Sum(REVENUE_CENTS)` | stride 20,500센트, orbit 4,500센트 |
| 30분 클릭 추이 | `EVENT_TS` Date histogram, 레코드 수, `BRAND` 분리 | 00:00 구간 3건, 00:30 구간 1건 |
| 페이지와 세션 | `PAGE_NAME`별 레코드 수, `SESSION_ID`의 Distinct count | product 3건, cart 1건, 세션 약 3개 |

Lens가 시간 간격을 자동 선택하면 최소 간격을 30분으로 설정하고, 조회 범위에서 실제로 30분 단위가 표시되는지 확인한다. 정확히 고정한 구간을 대조할 때는 아래 Elasticsearch 집계를 사용할 수 있다. 매출 인덱스는 최신값 뷰이므로 시간별 매출이 필요하면 주문 이벤트를 별도로 적재하거나, ksqlDB 윈도우 집계를 윈도우 시작과 그룹 키를 함께 담은 문서 ID로 저장한다. [Elastic · Kibana Lens](https://www.elastic.co/guide/en/kibana/8.17/lens.html) · [Elastic · Date Histogram](https://www.elastic.co/guide/en/elasticsearch/reference/8.17/search-aggregations-bucket-datehistogram-aggregation.html)

```bash
curl -fsS -X POST "$es_url/$click_topic/_search" \
  -H 'Content-Type: application/json' -d @- <<'JSON' | jq -e '[.aggregations.clicks.buckets[].doc_count] == [3, 1]'
{
  "size": 0,
  "query": {
    "range": {
      "EVENT_TS": { "gte": 1795132800000, "lt": 1795136400000 }
    }
  },
  "aggs": {
    "clicks": {
      "date_histogram": { "field": "EVENT_TS", "fixed_interval": "30m", "time_zone": "UTC" }
    }
  }
}
JSON
```
