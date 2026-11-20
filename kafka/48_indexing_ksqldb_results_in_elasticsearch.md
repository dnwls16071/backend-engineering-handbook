# Indexing ksqlDB Results in Elasticsearch

ksqlDB가 계산한 결과를 Kafka 토픽에 쓰면 Elasticsearch Sink가 각 레코드를 검색 가능한 문서로 색인한다. Elasticsearch는 문서를 저장하고 검색·집계 API를 제공한다. Kibana는 이 데이터를 조회해 시각화와 대시보드를 만든다. 이벤트 이력을 조회할 때는 레코드마다 문서를 만들고, 현재 상태를 조회할 때는 같은 키의 문서를 갱신한다. [Confluent · Elasticsearch Sink](https://docs.confluent.io/kafka-connectors/elasticsearch/current/overview.html) · [Elastic · Search API](https://www.elastic.co/docs/solutions/search/the-search-api) · [Elastic · Kibana](https://www.elastic.co/docs/explore-analyze)

## 1. Elasticsearch, Kibana, Sink 플러그인을 추가한다

47번에서 만든 `compose.ksqldb.yaml`과 `compose.ksql-connect.yaml` 위에 두 파일을 추가한다. Elasticsearch와 Kibana의 버전은 `8.17.4`로 맞춘다. Sink `16.0.1`은 Elasticsearch 8.x에서 동작하며, Elastic의 클라이언트 호환성 보증이 필요한 배포에서는 `8.19.x` 이상을 사용한다. 다음 Compose는 학습용 단일 노드에만 사용하며 호스트 포트는 루프백에 바인딩한다. [47번 Connect 실습](47_ingesting_ksqldb_data_with_kafka_connect_and_datagen.md) · [Confluent · Elasticsearch Sink 버전과 호환성](https://docs.confluent.io/kafka-connectors/elasticsearch/current/overview.html) · [Confluent · Sink Changelog](https://docs.confluent.io/kafka-connectors/elasticsearch/current/changelog.html) · [Elastic · Docker 실습](https://www.elastic.co/search-labs/tutorials/install-elasticsearch/docker)

`Dockerfile.ksql-search-connect`를 저장한다. 워커를 교체해도 앞의 Datagen 소스를 실행할 수 있도록 두 플러그인을 이미지에 포함한다.

```dockerfile
FROM confluentinc/cp-kafka-connect:7.9.11
USER root
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-datagen:0.6.4 \
    && confluent-hub install --no-prompt confluentinc/kafka-connect-elasticsearch:16.0.1
USER 1001
```

`compose.search.yaml`을 저장한다. Kibana와 Connect는 Compose 네트워크에서 `http://elasticsearch:9200`을 사용한다. 호스트에서는 검색 API의 `127.0.0.1:9200`과 Kibana의 `127.0.0.1:5601`로 접속한다.

```yaml
services:
  connect:
    image: ksql-lab-search-connect:7.9.11
    build:
      dockerfile: Dockerfile.ksql-search-connect
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.4
    ports:
      - '127.0.0.1:9200:9200'
    environment:
      discovery.type: single-node
      xpack.security.enabled: 'false'
      ES_JAVA_OPTS: '-Xms512m -Xmx512m'
    networks: [kafka-lab]
  kibana:
    image: docker.elastic.co/kibana/kibana:8.17.4
    ports:
      - '127.0.0.1:5601:5601'
    environment:
      ELASTICSEARCH_HOSTS: '["http://elasticsearch:9200"]'
    depends_on: [elasticsearch]
    networks: [kafka-lab]
```

```bash
search_compose() {
  docker compose -f compose.ksqldb.yaml -f compose.ksql-connect.yaml -f compose.search.yaml "$@"
}
search_compose up -d --build connect schema-registry ksqldb elasticsearch kibana
es_url=http://127.0.0.1:9200
connect_url=http://127.0.0.1:18083
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$es_url/" | jq '.version.number'
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -e '.[] | select(.class == "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector")'
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 http://127.0.0.1:18088/info
search_compose run --rm ksql-cli
```

## 2. 이벤트 스트림과 현재 상태 테이블을 만든다

CLI에서 키 없는 요청 스트림의 출력과 계정 상태 테이블의 출력에 다른 토픽을 지정한다. 토픽 이름을 Elasticsearch 인덱스 이름으로도 사용한다. 계정 테이블의 `ACCOUNT_ID`는 Kafka 키에 들어가며, 값에는 잔액과 상태가 들어간다. 다음 검증은 해당 토픽과 인덱스가 비어 있는 첫 실행 기준이다. [Confluent · Stream Processing](https://docs.confluent.io/platform/7.9/ksqldb/concepts/stream-processing.html) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html) · [Confluent · Elasticsearch Sink 인덱스 이름](https://docs.confluent.io/kafka-connectors/elasticsearch/current/overview.html)

```sql
SET 'auto.offset.reset' = 'earliest';

CREATE STREAM lab48_request_input (REQUEST_PATH STRING, STATUS_CODE INT) WITH (
    KAFKA_TOPIC = 'ksql.lab48.request_input.v1', PARTITIONS = 1,
    KEY_FORMAT = 'NONE', VALUE_FORMAT = 'JSON'
);
CREATE STREAM lab48_requests WITH (
    KAFKA_TOPIC = 'ksql.lab48.requests.v1',
    KEY_FORMAT = 'NONE', VALUE_FORMAT = 'JSON'
) AS SELECT REQUEST_PATH, STATUS_CODE
   FROM lab48_request_input
   WHERE STATUS_CODE >= 400
   EMIT CHANGES;

CREATE TABLE lab48_account_changes (
    ACCOUNT_ID STRING PRIMARY KEY, BALANCE BIGINT, STATUS STRING
) WITH (
    KAFKA_TOPIC = 'ksql.lab48.account_changes.v1', PARTITIONS = 1,
    KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON'
);
CREATE TABLE lab48_account_state WITH (
    KAFKA_TOPIC = 'ksql.lab48.account_state.v1',
    KEY_FORMAT = 'KAFKA', VALUE_FORMAT = 'JSON'
) AS SELECT ACCOUNT_ID, BALANCE, STATUS
   FROM lab48_account_changes
   EMIT CHANGES;
```

## 3. 두 출력 토픽을 서로 다른 문서 ID 정책으로 색인한다

| 출력 | Sink 설정 | 문서 ID와 기록 방식 |
| --- | --- | --- |
| 요청 이벤트 | `key.ignore=true`, `write.method=INSERT` | `topic+partition+offset`으로 ID를 구성한다. 같은 내용이 서로 다른 오프셋으로 들어오면 각각 기록되고, 동일 오프셋을 다시 처리할 때는 같은 ID를 사용한다. |
| 계정 상태 | `key.ignore=false`, `write.method=INSERT` | 문자열 Kafka 키를 `_id`로 쓰고 같은 ID의 전체 문서를 교체한다. Sink는 일반 인덱스에서 Kafka 오프셋을 외부 버전으로 사용하므로 같은 키가 같은 파티션에 유지되어야 한다. |

`schema.ignore=true`는 Connect 스키마로 매핑을 생성하는 동작을 끈다. 아래 JSON 예제는 Elasticsearch의 동적 매핑을 사용한다. 필드 타입과 검색 방식을 고정하려면 인덱스 또는 인덱스 템플릿에 매핑을 미리 정의한다. JSON의 값과 문자열 키는 각각 `JsonConverter`와 `StringConverter`로 읽는다. [Confluent · Elasticsearch Sink 설정](https://docs.confluent.io/kafka-connectors/elasticsearch/current/configuration_options.html) · [Elastic · Dynamic Mapping](https://www.elastic.co/docs/manage-data/data-store/mapping/dynamic-mapping)

호스트 셸에서 Connect REST에 설정을 등록한다. ksqlDB CLI에서 같은 속성을 `CREATE SINK CONNECTOR 이름 WITH (...)`로 전달할 수도 있다. `RUNNING` 상태의 작업이 있는지 확인한 뒤 다음 절의 데이터를 보낸다. [Confluent · Connect REST Interface](https://docs.confluent.io/platform/7.9/connect/references/restapi.html) · [Confluent · CREATE CONNECTOR](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-connector.html)

```bash
cat > request-search.json <<'JSON'
{
  "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
  "tasks.max": "1",
  "topics": "ksql.lab48.requests.v1",
  "connection.url": "http://elasticsearch:9200",
  "key.ignore": "true",
  "schema.ignore": "true",
  "write.method": "INSERT",
  "behavior.on.null.values": "IGNORE",
  "key.converter": "org.apache.kafka.connect.storage.StringConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "false"
}
JSON
jq '. + {"topics":"ksql.lab48.account_state.v1",
         "key.ignore":"false", "behavior.on.null.values":"DELETE"}' \
  request-search.json > account-search.json

put_search_sink() {
  curl -fsS -X PUT -H 'Content-Type: application/json' \
    --data-binary "@$2" "$connect_url/connectors/$1/config"
}
put_search_sink lab48-requests request-search.json
put_search_sink lab48-accounts account-search.json

for name in lab48-requests lab48-accounts; do
  curl -fsS "$connect_url/connectors/$name/status" |
    jq '{connector: .connector.state, tasks: [.tasks[] | {id, state, trace}]}'
done
```

## 4. 이벤트 두 건, 상태 교체, tombstone 삭제를 확인한다

CLI에서 같은 요청을 두 건 보내고, 계정 `acct-1`의 첫 상태를 기록한다. [Confluent · INSERT VALUES](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/insert-values.html)

```sql
INSERT INTO lab48_request_input (REQUEST_PATH, STATUS_CODE) VALUES ('/checkout', 503);
INSERT INTO lab48_request_input (REQUEST_PATH, STATUS_CODE) VALUES ('/checkout', 503);
INSERT INTO lab48_account_changes (ACCOUNT_ID, BALANCE, STATUS)
VALUES ('acct-1', 4200, 'OPEN');
```

호스트에서 결과를 조회한다. 두 요청 문서의 `_id`는 서로 다르고, `acct-1` 문서의 잔액은 `4200`이다. Kafka, ksqlDB, Connect의 처리는 비동기이므로 반영될 때까지 다시 조회한다. `_search`는 인덱스의 refresh 후 변경을 볼 수 있고, 단건 `_doc` 조회는 기본적으로 실시간이다. 같은 `GET <인덱스>/_search`를 Kibana Dev Tools에서 실행하거나, 요청 인덱스의 Data View를 만들어 Discover에서 문서를 볼 수 있다. [Elastic · Search API](https://www.elastic.co/docs/solutions/search/the-search-api) · [Elastic · Get API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-get) · [Elastic · Near Real-Time Search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search) · [Elastic · Data Views](https://www.elastic.co/docs/explore-analyze/find-and-organize/data-views)

```bash
curl -fsS "$es_url/ksql.lab48.requests.v1/_search?size=10&track_total_hits=true" |
  jq '{total: .hits.total.value, documents: [.hits.hits[] | {_id, _source}]}'
curl -fsS "$es_url/ksql.lab48.account_state.v1/_doc/acct-1" | jq '{_id, _source}'
```

다음 상태를 CLI에서 발행하고 위의 단건 조회를 반복한다. `_id`는 `acct-1`이고 문서는 `3000`, `HOLD`로 바뀐다. `INSERT`는 ksqlDB가 제공하는 전체 상태를 문서로 교체한다. 일부 필드만 유지·갱신해야 할 때는 `UPSERT`를 쓸 수 있다. 그 경로는 오프셋 기반 외부 버전을 사용하지 않으므로 요청 순서가 중요하면 `max.in.flight.requests=1`을 적용하고 재처리 동작도 확인한다. [Confluent · write.method 및 max.in.flight.requests](https://docs.confluent.io/kafka-connectors/elasticsearch/current/configuration_options.html)

```sql
INSERT INTO lab48_account_changes (ACCOUNT_ID, BALANCE, STATUS)
VALUES ('acct-1', 3000, 'HOLD');
```

업데이트가 보이면 같은 키와 Kafka null 값을 원본 테이블 토픽에 발행한다. 콘솔 프로듀서의 `null.marker`가 문자열 `<DELETE>`를 null 값으로 바꾼다. 이 변경 로그가 결과 토픽에 전달되면 `behavior.on.null.values=DELETE`가 `acct-1` 문서를 삭제한다. `_doc/acct-1`이 HTTP `404`와 `found:false`를 반환할 때까지 조회한다. [Apache Kafka · Console Producer](https://github.com/apache/kafka/blob/3.9.1/core/src/main/scala/kafka/tools/ConsoleProducer.scala) · [Confluent · ksqlDB의 null과 tombstone](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html) · [Confluent · Elasticsearch Sink null 처리](https://docs.confluent.io/kafka-connectors/elasticsearch/current/configuration_options.html)

```bash
printf '%s\n' 'acct-1|<DELETE>' | search_compose exec -T connect kafka-console-producer \
  --bootstrap-server "${KSQL_LAB_BOOTSTRAP:-kafka:29092}" \
  --topic ksql.lab48.account_changes.v1 \
  --property parse.key=true --property 'key.separator=|' --property 'null.marker=<DELETE>'
curl -sS -w '\nHTTP %{http_code}\n' "$es_url/ksql.lab48.account_state.v1/_doc/acct-1"
```

## 5. Avro 값과 복합 키를 다룬다

47번의 Avro 토픽을 색인하려면 값 converter를 `AvroConverter`로 바꾸고 워커에서 접근 가능한 Registry 주소를 넣는다. 입력 키는 여전히 UTF-8 문자열이므로 기존 key converter를 사용한다. `schema.ignore=false`일 때 Sink는 등록된 Avro 스키마로 복원한 Connect 스키마를 초기 매핑에 활용할 수 있다. IP가 같은 여러 이벤트를 보관하도록 `key.ignore=true`를 유지한다. [Confluent · Connect와 Schema Registry](https://docs.confluent.io/platform/7.9/schema-registry/connect.html) · [Confluent · Sink Mapping Inference](https://docs.confluent.io/kafka-connectors/elasticsearch/current/overview.html#mapping-inference)

```bash
jq 'del(."value.converter.schemas.enable") + {
  "topics": "ksql.lab47.clickstream.avro",
  "schema.ignore": "false",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}' request-search.json > clickstream-avro-search.json
put_search_sink lab48-clicks-avro clickstream-avro-search.json

curl -fsS "$es_url/ksql.lab47.clickstream.avro/_search?size=2" |
  jq '.hits.hits[] | {_id, ip: ._source.ip, status: ._source.status}'
```

47번에서 발행한 레코드가 남아 있으면 `ip`와 `status`를 가진 문서가 표시된다. Kafka 키도 Avro라면 `key.converter`와 `key.converter.schema.registry.url`을 실제 키 인코딩에 맞춰 지정한다. 복합 키를 문서 ID로 사용하려면 Sink가 읽기 전에 하나의 문자열 키로 변환한다. 예를 들어 두 필드를 정해진 순서의 JSON 배열로 직렬화하고 그 UTF-8 바이트를 Base64로 인코딩하면 아래 두 조합이 서로 다른 ID가 된다. 필드 순서·타입·null 처리 규칙을 고정하고, 갱신과 tombstone에도 같은 인코딩을 적용한다. Elasticsearch의 `_id` 한도는 512바이트다. [Confluent · Multi-Column Keys](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html) · [Elastic · _id field](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/mapping-id-field)

```bash
jq -nr '["a-b","c"], ["a","b-c"] | @base64'
# WyJhLWIiLCJjIl0=
# WyJhIiwiYi1jIl0=
```

## 6. 운영 계정을 분리하고 실패 지점을 좁힌다

인증을 켠 환경에서는 Sink 전용 계정과 HTTPS를 사용한다. Confluent 예제 역할은 버전 확인에 필요한 클러스터 `monitor`와 대상 인덱스에 대한 `create_index`, `read`, `write`, `view_index_metadata`를 부여한다. 대상은 이 Sink가 쓰는 인덱스 이름으로 제한한다. Kibana 조회 계정에는 해당 인덱스의 `read`, `view_index_metadata`와 사용하는 Kibana Space의 기능 권한을 부여한다. [Confluent · Sink 설치와 필요 권한](https://docs.confluent.io/kafka-connectors/elasticsearch/current/overview.html#prerequisites) · [Elastic · Elasticsearch Privileges](https://www.elastic.co/docs/reference/elasticsearch/security-privileges) · [Elastic · Kibana Role Management](https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/kibana-role-management)

결과가 비어 있으면 먼저 `PRINT`로 ksqlDB 출력 토픽에 레코드가 있는지 확인한다. Connect의 `/status`에서 Task의 `trace`를 보고 변환 오류와 Elasticsearch 응답 오류를 구분한다. 인증·권한 오류는 워커의 접속 주소와 전용 역할을, 문서 거부는 `GET <인덱스>/_mapping`의 필드 타입을 확인한다. `_doc`에 문서가 있고 `_search`에 아직 없다면 refresh 이후 검색한다. [Confluent · Kafka Connect REST API](https://docs.confluent.io/platform/7.9/connect/references/restapi.html) · [Confluent · Malformed Documents](https://docs.confluent.io/kafka-connectors/elasticsearch/current/configuration_options.html) · [Elastic · Near Real-Time Search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search)
