# Integrating Kafka Connect with Avro and Schema Registry

Debezium은 Connect 스키마와 값을 만들고, 소스의 `AvroConverter`가 이를 Avro 바이트로 직렬화한다. 기본 Confluent 와이어 형식은 매직 바이트와 writer schema ID 뒤에 Avro payload를 담는다. JDBC Sink의 `AvroConverter`는 그 ID로 Schema Registry에서 스키마를 찾아 Connect 스키마와 값을 복원한다. [Confluent · Avro Serializer and Deserializer](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/serdes-avro.html) · [Confluent · Kafka Connect with Schema Registry](https://docs.confluent.io/platform/current/schema-registry/connect.html)

## 1. Schema Registry 실행과 Avro 메시지 왕복

[01번 Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)의 `compose.yaml` 옆에 `compose.registry.yaml`을 둔다. Registry는 Kafka의 `kafka:29092`를 사용하고 단일 브로커 실습에서는 내부 `_schemas` 토픽의 복제 계수를 `1`로 설정한다. 호스트의 `curl`은 `127.0.0.1:8081`, 다른 Compose 서비스는 `schema-registry:8081`을 사용한다. [Confluent · Docker Image Configuration](https://docs.confluent.io/platform/current/installation/docker/config-reference.html) · [Confluent · Schema Registry Configuration](https://docs.confluent.io/platform/current/schema-registry/installation/config.html)

```yaml
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:8.2.4
    depends_on:
      kafka: { condition: service_healthy }
    ports: ["127.0.0.1:8081:8081"]
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: PLAINTEXT://kafka:29092
      SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR: "1"
```

`kafka-avro-console-producer`에 줄 단위 JSON을 넣고, `kafka-avro-console-consumer`에서 Avro가 다시 JSON으로 표시되는지 확인한다. 두 CLI는 Schema Registry 컨테이너에서 실행하므로 Registry 주소로 `localhost:8081`을 쓴다. 아래 스키마는 값에만 적용하며, 실행마다 다른 토픽을 만든다. 이후 예시는 같은 셸에서 진행한다. [Confluent · Avro 콘솔 실습](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/serdes-avro.html) · [Confluent · Schema Registry 컨테이너에서 CLI 실행](https://github.com/confluentinc/agent-skills/blob/main/skills/kafka-streams-programming/references/docker-compose.md)

```bash
registry_compose() { docker compose -f compose.yaml -f compose.registry.yaml "$@"; }
registry_compose up -d --wait
registry=http://127.0.0.1:8081
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$registry/subjects" | jq .

run_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
topic="avro-console-$run_id"
order_v1='{"type":"record","name":"Order","namespace":"lab.avro","fields":[{"name":"id","type":"long"}]}'
registry_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic "$topic" --partitions 1 --replication-factor 1
printf '%s\n' '{"id":1}' | registry_compose exec -T schema-registry kafka-avro-console-producer \
  --bootstrap-server kafka:29092 --topic "$topic" \
  --property schema.registry.url=http://localhost:8081 --property "value.schema=$order_v1"
registry_compose exec -T schema-registry kafka-avro-console-consumer \
  --bootstrap-server kafka:29092 --topic "$topic" --from-beginning \
  --max-messages 1 --timeout-ms 30000 --property schema.registry.url=http://localhost:8081 |
  jq -e '.id == 1'
curl -fsS "$registry/subjects/$topic-value/versions/latest" | jq '{subject, version, id, schema}'
```

## 2. Subject, 버전, Connect 스키마

기본 `TopicNameStrategy`는 키와 값을 각각 `<topic>-key`, `<topic>-value` subject에 등록한다. Subject에는 스키마 버전과 유효 호환성 정책이 있다. Kafka 레코드의 schema ID로 writer schema를 조회하고, subject와 version으로 해당 계약의 변경 이력을 조회한다. 콘솔 실습은 값만 직렬화하므로 `-value` subject만 생긴다. CDC에서 키의 Avro 스키마를 바꾸면 직렬화된 키 바이트와 파티션 선택에 영향을 줄 수 있으므로 값의 스키마와 별도로 검토한다. [Confluent · Subject Name Strategy and Wire Format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html) · [Confluent · Schema Registry API](https://docs.confluent.io/platform/current/schema-registry/develop/api.html)

| Converter 설정 | Kafka에 저장되는 형식 | JDBC Sink에서 사용할 수 있는 스키마 |
| --- | --- | --- |
| `JsonConverter` + `schemas.enable=false` | 데이터만 담은 JSON | Connect 스키마가 없어 일반적인 JDBC 행 매핑에 사용할 수 없다. |
| `JsonConverter` + `schemas.enable=true` | `schema`와 `payload`를 포함한 JSON | 인라인 Connect 스키마를 복원한다. |
| `AvroConverter` + `schema.registry.url` | schema ID가 붙은 Avro 바이트 | Registry의 writer schema로 Connect 스키마를 복원한다. |

`schemas.enable`은 `JsonConverter` 설정이다. Registry를 사용하는 JSON Schema converter는 `io.confluent.connect.json.JsonSchemaConverter`다. 소스와 Sink에는 키와 값 각각의 인코딩에 맞는 converter를 설정한다. [Confluent · Kafka Connect Converters](https://docs.confluent.io/platform/current/connect/userguide.html) · [Confluent · Connect와 스키마](https://docs.confluent.io/platform/current/schema-registry/connect.html)

## 3. 호환성 허용과 거부 확인

`BACKWARD`는 새 reader schema가 직전 writer schema의 데이터를 읽을 수 있는지 검사한다. `FORWARD`는 기존 reader가 새 writer의 데이터를 읽는 방향이다. `FULL`은 두 방향을 모두 검사하고, `*_TRANSITIVE`는 모든 이전 버전을 검사한다. `BACKWARD`일 때 `default: null`인 nullable 필드를 추가하면 새 reader는 이전 데이터의 누락 필드를 `null`로 채울 수 있다. 기본값 없이 필수 필드를 추가하면 이전 데이터에 그 값을 채울 방법이 없다. [14번 Avro 스키마 변경](14_evolving_kafka_event_schemas_with_avro.md#2-호환성-방향과-배포-순서) · [Confluent · Schema Evolution and Compatibility](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html) · [Apache Avro · Schema Resolution](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution)

매번 별도 subject에 `BACKWARD`를 적용한다. 두 후보를 v1에 대해 검사한 뒤 허용된 후보만 등록하고, 거부된 후보를 등록하려고 하면 HTTP `409`가 오는지 확인한다. Registry 전체 정책과 CDC 토픽 subject는 기존 설정으로 운영할 수 있다. [Confluent · Schema Registry API](https://docs.confluent.io/platform/current/schema-registry/develop/api.html)

```bash
(
  set -euo pipefail
  subject="avro-compat-$(uuidgen | tr '[:upper:]' '[:lower:]')-value"
  content_type='Content-Type: application/vnd.schemaregistry.v1+json'
  versions="$registry/subjects/$subject/versions"
  check="$registry/compatibility/subjects/$subject/versions/latest?verbose=true"
  pack_schema() { jq -cn --arg schema "$1" '{schemaType: "AVRO", schema: $schema}'; }
  add_field() { jq -c --argjson field "$1" '.fields += [$field]' <<<"$order_v1"; }
  compatible=$(add_field '{"name":"couponCode","type":["null","string"],"default":null}')
  incompatible=$(add_field '{"name":"requiredCode","type":"string"}')

  curl -fsS -X PUT -H "$content_type" --data '{"compatibility":"BACKWARD"}' \
    "$registry/config/$subject" | jq -e '.compatibility == "BACKWARD"'
  curl -fsS -H "$content_type" --data "$(pack_schema "$order_v1")" "$versions" | jq -e '.id'
  curl -fsS -H "$content_type" --data "$(pack_schema "$compatible")" "$check" | jq -e '.is_compatible'
  curl -fsS -H "$content_type" --data "$(pack_schema "$incompatible")" "$check" |
    jq -e 'select(.is_compatible == false)'
  curl -fsS -H "$content_type" --data "$(pack_schema "$compatible")" "$versions" | jq -e '.id'

  response=$(mktemp)
  trap 'rm -f "$response"' EXIT
  status=$(curl -sS -o "$response" -w '%{http_code}' -H "$content_type" \
    --data "$(pack_schema "$incompatible")" "$versions")
  test "$status" = 409
  jq -e '.message | strings | select(length > 0)' "$response"
  curl -fsS "$versions" | jq -e '. == [1, 2]'
)
```

## 4. Debezium Source와 JDBC Sink에 Avro 적용

[38번 PostgreSQL CDC 실습의 준비 및 등록 절](38_capturing_postgresql_changes_with_debezium_and_jdbc_sink.md#2-postgresql과-connect-준비)에서 PostgreSQL과 JDBC 플러그인을 준비하고 `pg-source.json`, `pg-sink.json`을 만든다. 워커는 `127.0.0.1:18084`에서 접속한다. [08번 FileStream 실습](08_building_and_operating_kafka_connect_pipelines.md#4-docker에서-분산-워커-실행하기)의 Connect REST는 `18083`이다. Debezium 이미지에 Confluent converter와 의존 JAR을 추가해야 한다. Debezium의 설치 목록에 따라 호환되는 버전의 JAR을 `plugins/avro/`에 모으고 다음을 `compose.avro-connect.yaml`에 저장한다. [Debezium · Confluent Schema Registry 설치](https://debezium.io/documentation/reference/3.7/configuration/avro.html#deploying-confluent-schema-registry-with-debezium-containers) · [Debezium · Connect 이미지 플러그인 경로](https://github.com/debezium/container-images/blob/main/connect-base/3.7/Dockerfile)

```yaml
services:
  debezium:
    volumes:
      - ./plugins/avro:/kafka/connect/confluent-avro:ro
```

양쪽 커넥터에 `key.converter`, `value.converter`와 각 `schema.registry.url`을 모두 지정한다. Avro 소스에 전용 publication, 복제 슬롯과 토픽 접두사를 주고, `schema.name.adjustment.mode=avro`로 접두사의 `-`가 들어간 스키마 이름을 변환한다. 토픽 `pg38-avro.public.orders_pg38`에는 Avro 레코드가 쌓이고, Sink는 `cdc_sink.public.orders_pg38_avro`에 기록한다. 직렬화 방식이 바뀌는 기존 파이프라인도 토픽을 새로 만들면 소비자가 처음부터 한 가지 형식으로 읽을 수 있다. [Confluent · Connect Converter 설정](https://docs.confluent.io/platform/current/schema-registry/connect.html) · [Debezium · PostgreSQL Connector Properties](https://debezium.io/documentation/reference/3.7/connectors/postgresql.html#postgresql-connector-properties)

```bash
avro_cdc_compose() {
  docker compose -f compose.yaml -f compose.cdc.yaml -f compose.pg-jdbc.yaml \
    -f compose.registry.yaml -f compose.avro-connect.yaml "$@"
}
avro_cdc_compose up -d --wait
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$registry/subjects" | jq .
connect=http://127.0.0.1:18084
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect/connector-plugins" | jq .
pg_cdc_sql <<'SQL'
SELECT 'CREATE PUBLICATION pg38_avro_pub FOR TABLE public.orders_pg38'
WHERE NOT EXISTS (SELECT FROM pg_publication WHERE pubname = 'pg38_avro_pub')
\gexec
SQL

avro_converters='del(."key.converter.schemas.enable", ."value.converter.schemas.enable")
  | . + {"key.converter":"io.confluent.connect.avro.AvroConverter",
         "value.converter":"io.confluent.connect.avro.AvroConverter",
         "key.converter.schema.registry.url":"http://schema-registry:8081",
         "value.converter.schema.registry.url":"http://schema-registry:8081"}'

jq "$avro_converters"' | . + {"slot.name":"pg38_avro_slot", "publication.name":"pg38_avro_pub",
  "topic.prefix":"pg38-avro", "schema.name.adjustment.mode":"avro"}' \
  pg-source.json > pg-source-avro.json
jq "$avro_converters"' | . + {"topics":"pg38-avro.public.orders_pg38", "table.name.format":"public.orders_pg38_avro"}' \
  pg-sink.json > pg-sink-avro.json
pg_put pg38-avro-source pg-source-avro.json
pg_put pg38-avro-sink pg-sink-avro.json
for connector in pg38-avro-source pg38-avro-sink; do
  curl -fsS "$connect/connectors/$connector/status" | jq '{name, connector, tasks}'
done
```

양쪽 작업이 `RUNNING`이면 주문을 한 건 upsert한다. 새 토픽에서 키·값 subject가 등록되고 Avro 이벤트를 읽을 수 있는지 확인한다. 대상 DB에는 `id=36`, `status='avro'`가 나타날 때까지 조회한다. [Confluent · Avro 콘솔 실습](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/serdes-avro.html) · [Confluent · JDBC Sink Upsert](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

```bash
pg_cdc_sql <<'SQL'
INSERT INTO public.orders_pg38 (id, status) VALUES (36, 'avro')
ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status;
SQL
cdc_topic=pg38-avro.public.orders_pg38
avro_cdc_compose exec -T schema-registry kafka-avro-console-consumer \
  --bootstrap-server kafka:29092 --topic "$cdc_topic" --from-beginning \
  --max-messages 1 --timeout-ms 30000 --property schema.registry.url=http://localhost:8081 \
  --property print.key=true
for part in key value; do
  curl -fsS "$registry/subjects/$cdc_topic-$part/versions/latest" | jq '{subject, version, id}'
done
pg_sink_sql -c 'SELECT id, status FROM public.orders_pg38_avro WHERE id = 36;'
```
