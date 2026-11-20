# Evolving Kafka Event Schemas with Avro

Kafka 토픽에 여러 버전의 레코드가 섞여 있으면 새 소비자도 이전 데이터를 읽을 수 있어야 한다. Apache Avro는 스키마로 레코드의 구조와 바이너리 인코딩을 정의한다. Confluent Schema Registry는 스키마를 등록하고 조회하는 API와 버전 간 호환성 검사를 제공한다. [Apache Avro · Specification](https://avro.apache.org/docs/1.12.0/specification/) · [Confluent · Schema Evolution](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)

## 1. 레코드에 사용한 스키마 찾기

Avro의 **writer schema**는 값을 기록할 때 사용한 스키마다. **Reader schema**는 읽는 애플리케이션이 기대하는 스키마다. Avro는 레코드 필드를 이름으로 맞추고, writer에 없는 필드에 reader 기본값이 있으면 그 값으로 채운다. Writer에만 있는 필드는 reader가 건너뛴다. [Apache Avro · Schema Resolution](https://avro.apache.org/docs/1.12.0/specification/#schema-resolution)

Confluent Avro 직렬화기의 기본 payload 형식은 버전 바이트 `0`, 4바이트 schema ID, Avro 바이너리 데이터 순이다. 역직렬화기는 schema ID로 Registry에서 writer schema를 찾는다. Java에서는 값 직렬화기에 `KafkaAvroSerializer`, 역직렬화기에 `KafkaAvroDeserializer`를 사용하고 양쪽에 `schema.registry.url`을 설정한다. 생성한 Avro 클래스로 값을 읽으려면 소비자에 `specific.avro.reader=true`를 설정한다. [Confluent · Wire Format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#wire-format) · [Confluent · Avro SerDes](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/serdes-avro.html)

| 항목 | 의미 |
| --- | --- |
| Subject | 호환성 정책과 버전 이력을 적용하는 이름이다. 기본 `TopicNameStrategy`는 토픽 이름 뒤에 `-key` 또는 `-value`를 붙인다. |
| Schema ID | 레코드에 사용한 스키마를 식별한다. 동일한 스키마를 여러 subject에 등록하면 같은 ID를 공유할 수 있다. |
| Version | 각 subject 안에서 매겨지는 스키마 버전 번호다. `GET /subjects/{subject}/versions/{version}`에서 스키마와 ID를 함께 조회할 수 있다. |

키와 값의 스키마를 각각 관리한다. Avro 키의 schema ID가 바뀌면 직렬화된 키 바이트도 달라진다. 이 경우 로그 컴팩션은 두 레코드를 서로 다른 키로 처리하며, 기본 키 기반 파티셔닝에서도 배치가 달라질 수 있다. [Confluent · Subject Name Strategy](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#subject-name-strategy) · [Confluent · API Reference](https://docs.confluent.io/platform/current/schema-registry/develop/api.html) · [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#partitioner.class) · [Apache Kafka · Log Compaction](https://kafka.apache.org/43/design/design/#log_compaction)

## 2. 호환성 방향과 배포 순서

| 정책 | 검사 방향 | 배포 순서 |
| --- | --- | --- |
| `BACKWARD` | 새 reader가 이전 writer의 데이터를 읽는다. | 소비자부터 갱신한다. |
| `FORWARD` | 이전 reader가 새 writer의 데이터를 읽는다. | 생산자부터 갱신한다. |
| `FULL` | 두 방향을 모두 만족한다. | 생산자와 소비자를 독립적으로 갱신할 수 있다. |

Confluent Registry 기본값은 `BACKWARD`이며 바로 이전 버전과 비교한다. 정책에 `_TRANSITIVE`를 붙이면 등록된 이전 버전 전체와 비교한다. 보관 중인 오래된 이벤트를 처음부터 재처리한다면 `BACKWARD_TRANSITIVE`로 확인한다. 호환성 검사에 더해 실제 소비자의 필드 해석도 테스트한다. 예를 들어 `currency`의 기본값이 기존 주문의 통화와 일치하는지 확인한다. [Confluent · Compatibility Types](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)

## 3. 주문 스키마 등록과 호환성 확인

로컬에서 Confluent Schema Registry가 `http://localhost:8081`에 실행 중이고 `jq`를 사용할 수 있다고 가정한다. 새 subject에 `orderId`만 있는 스키마를 등록한 뒤, 기본값이 `null`인 `couponCode` 필드를 추가한다. 새 reader는 이전 주문에서 해당 필드를 `null`로 읽는다. [Confluent · Schema Registry API](https://docs.confluent.io/platform/current/schema-registry/develop/api.html) · [Apache Avro · Records](https://avro.apache.org/docs/1.12.0/specification/#records)

```bash
(
  set -euo pipefail
  registry=${SCHEMA_REGISTRY_URL:-http://localhost:8081}
  subject=avro-order-demo-value
  content_type='Content-Type: application/vnd.schemaregistry.v1+json'
  versions="$registry/subjects/$subject/versions"
  v1='{"type":"record","name":"OrderPlaced","namespace":"example.orders","fields":[{"name":"orderId","type":"string"}]}'
  v2=$(jq -c '.fields += [{"name":"couponCode","type":["null","string"],"default":null}]' <<< "$v1")
  payload() { jq -nc --arg schema "$1" '{schemaType:"AVRO",schema:$schema}'; }

  curl -fsS -H "$content_type" -d "$(payload "$v1")" "$versions" | jq .
  curl -fsS -X PUT -H "$content_type" -d '{"compatibility":"BACKWARD_TRANSITIVE"}' \
    "$registry/config/$subject" | jq .
  curl -fsS -H "$content_type" -d "$(payload "$v2")" \
    "$registry/compatibility/subjects/$subject/versions/latest?verbose=true" |
    jq -e '.is_compatible == true'
  curl -fsS -H "$content_type" -d "$(payload "$v2")" "$versions" | jq .
  curl -fsS "$versions/latest" | jq '{subject, version, id}'
)
```

새 subject에서 마지막 응답의 `version`은 `2`다. 검사에서 `is_compatible: false`가 반환되면 위 스크립트는 v2 등록 전에 종료한다. 배포 파이프라인에서 스키마를 사전 등록한다면 생산자의 `auto.register.schemas=false`를 지정해 발행 시점에 새 스키마가 자동으로 추가되지 않도록 한다. [Confluent · Schema Registry API](https://docs.confluent.io/platform/current/schema-registry/develop/api.html) · [Confluent · Serializer Configuration](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#handling-differences-between-preregistered-and-client-derived-schemas)
