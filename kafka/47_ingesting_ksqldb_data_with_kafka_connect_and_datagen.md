# Ingesting ksqlDB Data with Kafka Connect and Datagen

Datagen 소스 커넥터가 테스트용 클릭 이벤트를 Kafka에 발행하고, ksqlDB는 이 토픽을 스트림으로 읽는다. `CREATE SOURCE CONNECTOR`는 Connect 워커에 커넥터를 등록한다. `CREATE STREAM`은 토픽의 키와 값을 SQL에서 읽을 수 있도록 선언한다. 커넥터와 스트림은 각각 등록한다. [Confluent · Connectors in ksqlDB](https://docs.confluent.io/platform/7.9/ksqldb/concepts/connectors.html) · [Confluent · Kafka Connect Datagen](https://docs.confluent.io/kafka-connectors/datagen/current/overview.html)

## 1. Connect 워커의 실행 위치를 정한다

| 모드 | ksqlDB 서버 설정 | 플러그인을 설치할 위치 |
| --- | --- | --- |
| 외부 Connect | `ksql.connect.url=http://connect:8083`. Docker 이미지에서는 `KSQL_KSQL_CONNECT_URL`을 사용한다. | 외부 분산 Connect 워커 각각의 `plugin.path` |
| 내장 Connect | `ksql.connect.worker.config`에 컨테이너나 호스트에서 읽을 수 있는 워커 properties 파일의 경로를 지정한다. | Connect를 실행하는 각 ksqlDB 서버의 워커 `plugin.path` |

내장 워커 설정 파일에는 `bootstrap.servers`, `group.id`, 키와 값의 converter, 설정·오프셋·상태 저장 토픽, `plugin.path`를 지정한다. Confluent Docker 이미지는 `KSQL_CONNECT_GROUP_ID`, `KSQL_CONNECT_PLUGIN_PATH` 같은 워커 환경 변수로 설정 파일을 생성할 수도 있다. 단일 브로커에서는 세 내부 토픽의 복제 계수를 각각 `1`로 설정한다. 외부 모드에서는 `ksql.connect.worker.config`를 비워 두고 Connect를 독립적으로 배포한다. 다음 실습은 외부 모드를 사용한다. [Confluent · Manage Connectors](https://docs.confluent.io/platform/7.9/ksqldb/how-to-guides/use-connector-management.html) · [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html)

## 2. Datagen 플러그인이 있는 외부 워커를 추가한다

39번의 Kafka 네트워크와 `compose.ksqldb.yaml`을 사용한다. 같은 디렉터리에 `Dockerfile.ksql-connect`와 `compose.ksql-connect.yaml`을 저장한다. Connect 워커가 Marketplace에서 받은 Datagen 패키지를 찾도록 설치 디렉터리를 워커의 플러그인 경로에 포함한다. 플러그인 버전을 바꿀 때는 워커 이미지를 다시 빌드하고 컨테이너를 교체한다. [39번 ksqlDB 실습](39_understanding_ksqldb_architecture_and_parallelism.md) · [Confluent · Connect 이미지 확장](https://docs.confluent.io/platform/7.9/connect/extending.html) · [Confluent · Docker 환경 변수](https://docs.confluent.io/platform/7.9/installation/docker/config-reference.html)

```dockerfile
FROM confluentinc/cp-kafka-connect:7.9.11
USER root
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-datagen:0.6.4
USER 1001
```

```yaml
services:
  connect:
    image: ksql-lab-connect:7.9.11
    build:
      context: .
      dockerfile: Dockerfile.ksql-connect
    ports:
      - '127.0.0.1:18083:8083'
    environment:
      CONNECT_BOOTSTRAP_SERVERS: '${KSQL_LAB_BOOTSTRAP:-kafka:29092}'
      CONNECT_REST_ADVERTISED_HOST_NAME: connect
      CONNECT_GROUP_ID: ksql-lab-connect
      CONNECT_CONFIG_STORAGE_TOPIC: ksql-lab-connect-configs
      CONNECT_OFFSET_STORAGE_TOPIC: ksql-lab-connect-offsets
      CONNECT_STATUS_STORAGE_TOPIC: ksql-lab-connect-status
      CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR: '1'
      CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR: '1'
      CONNECT_STATUS_STORAGE_REPLICATION_FACTOR: '1'
      CONNECT_KEY_CONVERTER: org.apache.kafka.connect.storage.StringConverter
      CONNECT_VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_VALUE_CONVERTER_SCHEMAS_ENABLE: 'false'
      CONNECT_PLUGIN_PATH: /usr/share/java,/usr/share/confluent-hub-components
    networks: [kafka-lab]
  schema-registry:
    image: confluentinc/cp-schema-registry:7.9.11
    ports:
      - '127.0.0.1:8081:8081'
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: 'PLAINTEXT://${KSQL_LAB_BOOTSTRAP:-kafka:29092}'
      SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR: '1'
    networks: [kafka-lab]
  ksqldb:
    environment:
      KSQL_KSQL_CONNECT_URL: http://connect:8083
      KSQL_KSQL_SCHEMA_REGISTRY_URL: http://schema-registry:8081
```

호스트에서는 Connect REST 포트 `18083`, Registry 포트 `8081`에 접속한다. 컨테이너 사이에서는 서비스 이름과 컨테이너 포트를 사용한다. `GET /connector-plugins` 결과에 Datagen 클래스가 있으면 워커가 플러그인을 읽은 것이다. 브로커의 자동 토픽 생성 설정과 관계없이 실행할 수 있도록 소스 토픽을 미리 만든다. [Confluent · Connect REST Interface](https://docs.confluent.io/platform/7.9/connect/references/restapi.html)

```bash
ksql_connect_compose() {
  docker compose -f compose.ksqldb.yaml -f compose.ksql-connect.yaml "$@"
}
ksql_connect_compose up -d --build connect schema-registry ksqldb
connect_url=http://127.0.0.1:18083
registry_url=http://127.0.0.1:8081
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -e '.[] | select(.class == "io.confluent.kafka.connect.datagen.DatagenConnector")'
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$registry_url/subjects" | jq .
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 http://127.0.0.1:18088/info

for format in json avro; do
  ksql_connect_compose exec -T connect kafka-topics \
    --bootstrap-server "${KSQL_LAB_BOOTSTRAP:-kafka:29092}" \
    --create --if-not-exists --topic "ksql.lab47.clickstream.$format" \
    --partitions 1 --replication-factor 1
done
ksql_connect_compose run --rm ksql-cli
```

## 3. JSON 클릭 이벤트를 만들고 키 타입을 맞춘다

Datagen 0.6.4의 `clickstream` 템플릿은 `ip`를 문자열 키로 선택한다. 같은 `ip` 필드가 값에도 들어 있다. `StringConverter`는 키를 UTF-8 텍스트로 쓰므로 스트림은 `IP_KEY STRING KEY`와 `KEY_FORMAT='KAFKA'`로 읽는다. 값은 `JsonConverter`에서 `schemas.enable=false`로 직렬화해 JSON 객체만 기록한다. 번들 스키마의 `userid`는 정수, `_time`은 long이고 `status`와 `bytes`는 문자열이다. [Confluent · Datagen 0.6.4 키 설정](https://github.com/confluentinc/kafka-connect-datagen/blob/v0.6.4/src/main/java/io/confluent/kafka/connect/datagen/Quickstart.java) · [Confluent · Clickstream 스키마](https://github.com/confluentinc/kafka-connect-datagen/blob/v0.6.4/src/main/resources/clickstream_schema.avro) · [Confluent · ksqlDB Serialization Formats](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html)

```sql
CREATE SOURCE CONNECTOR IF NOT EXISTS clickstream_json_47 WITH (
    'connector.class' = 'io.confluent.kafka.connect.datagen.DatagenConnector',
    'tasks.max' = '1',
    'kafka.topic' = 'ksql.lab47.clickstream.json',
    'quickstart' = 'clickstream',
    'schema.keyfield' = 'ip',
    'max.interval' = '750',
    'key.converter' = 'org.apache.kafka.connect.storage.StringConverter',
    'value.converter' = 'org.apache.kafka.connect.json.JsonConverter',
    'value.converter.schemas.enable' = 'false'
);

SHOW CONNECTORS;
DESCRIBE CONNECTOR clickstream_json_47;
PRINT 'ksql.lab47.clickstream.json' FROM BEGINNING LIMIT 3;

CREATE STREAM IF NOT EXISTS clicks_json_47 (
    IP_KEY STRING KEY,
    IP STRING,
    USERID INT,
    _TIME BIGINT,
    REQUEST STRING,
    STATUS STRING,
    BYTES STRING
) WITH (
    KAFKA_TOPIC = 'ksql.lab47.clickstream.json',
    KEY_FORMAT = 'KAFKA',
    VALUE_FORMAT = 'JSON'
);

SET 'auto.offset.reset' = 'earliest';
SELECT IP_KEY, IP, USERID, STATUS
FROM clicks_json_47
EMIT CHANGES LIMIT 3;
```

커넥터와 Task가 `RUNNING`이면 토픽에서 생성된 JSON을 확인할 수 있다. Datagen이 만든 주소와 상태 값은 매번 달라지며, 같은 행의 `IP_KEY`와 `IP`는 일치한다. `PRINT`는 Kafka 레코드를 보여 주고 `SELECT`는 스트림 스키마로 해석한 행을 보여 준다. 다른 템플릿으로 바꾸면 키의 타입도 다시 확인한다. 예를 들어 `clickstream_codes`의 `code`를 32비트 정수 바이트로 직렬화하려면 `IntegerConverter`를 쓰고 ksqlDB에 `INT KEY`를 선언한다. [Confluent · CREATE CONNECTOR](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/create-connector.html) · [Confluent · Clickstream 튜토리얼](https://docs.confluent.io/platform/7.9/ksqldb/tutorials/clickstream.html)

## 4. Avro 값과 Registry subject를 확인한다

Datagen은 생성 규칙을 Avro 스키마로 표현한다. Kafka에 실제로 기록되는 형식은 converter가 결정한다. 다음 설정에서는 기존과 같은 문자열 키와 별도 Avro 값 토픽을 사용한다. 커넥터의 `value.converter.schema.registry.url`은 값을 직렬화할 때 쓸 Registry 주소다. ksqlDB 서버의 `ksql.schema.registry.url`은 스트림을 선언하고 값을 읽을 때 쓸 주소다. [Confluent · Kafka Connect Datagen](https://github.com/confluentinc/kafka-connect-datagen#confusion-about-schemas-and-avro) · [36번 Connect와 Avro](36_integrating_kafka_connect_with_avro_and_schema_registry.md) · [Confluent · ksqlDB의 Schema Registry 설정](https://docs.confluent.io/platform/current/ksqldb/operate-and-deploy/installation/avro-schema.html)

```sql
CREATE SOURCE CONNECTOR IF NOT EXISTS clickstream_avro_47 WITH (
    'connector.class' = 'io.confluent.kafka.connect.datagen.DatagenConnector',
    'tasks.max' = '1',
    'kafka.topic' = 'ksql.lab47.clickstream.avro',
    'quickstart' = 'clickstream',
    'schema.keyfield' = 'ip',
    'max.interval' = '750',
    'key.converter' = 'org.apache.kafka.connect.storage.StringConverter',
    'value.converter' = 'io.confluent.connect.avro.AvroConverter',
    'value.converter.schema.registry.url' = 'http://schema-registry:8081'
);
DESCRIBE CONNECTOR clickstream_avro_47;
```

별도 호스트 셸에서 값 subject의 등록을 확인한다. 여기서는 기본 `TopicNameStrategy`에 따라 `ksql.lab47.clickstream.avro-value`가 등록된다. 키는 `StringConverter`가 처리하므로 이 커넥터는 키 subject를 등록하지 않는다. [Confluent · Schema Registry API](https://docs.confluent.io/platform/7.9/schema-registry/develop/api.html) · [Confluent · Subject Name Strategy](https://docs.confluent.io/platform/7.9/schema-registry/fundamentals/serdes-develop/index.html)

```bash
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 \
  http://127.0.0.1:8081/subjects/ksql.lab47.clickstream.avro-value/versions/latest |
  jq -e '{subject, version, id, fields: (.schema | fromjson | .fields | map(.name))}'
```

같은 CLI에서 키 컬럼을 명시하고 값 컬럼은 등록된 스키마에서 가져온다. 조회 결과에 JSON 실습과 동일한 타입의 `IP`, `USERID`, `STATUS`가 표시된다. [Confluent · Schema Inference](https://docs.confluent.io/platform/current/ksqldb/operate-and-deploy/schema-registry-integration.html#with-partial-schema-inference) · [Confluent · Serialization Formats](https://docs.confluent.io/platform/7.9/ksqldb/reference/serialization.html)

```sql
CREATE STREAM IF NOT EXISTS clicks_avro_47 (IP_KEY STRING KEY) WITH (
    KAFKA_TOPIC = 'ksql.lab47.clickstream.avro',
    KEY_FORMAT = 'KAFKA',
    VALUE_FORMAT = 'AVRO'
);
DESCRIBE clicks_avro_47;
SELECT IP_KEY, IP, USERID, STATUS
FROM clicks_avro_47
EMIT CHANGES LIMIT 3;
```

## 5. 등록 상태와 데이터 흐름을 점검한다

`SHOW CONNECTORS`에 이름이 있어도 Task가 실패할 수 있다. `DESCRIBE CONNECTOR` 또는 Connect REST의 `/connectors/<이름>/status`에서 각 Task의 상태와 오류를 확인한다. 플러그인이 목록에 빠졌다면 워커 이미지와 `plugin.path`를 확인한다. Task는 정상인데 SQL에서 값이 나오지 않으면 토픽의 실제 converter, 선언한 키·값 형식, Registry subject와 소비 시작 위치를 확인한다. [Confluent · DESCRIBE CONNECTOR](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/describe-connector.html) · [Confluent · Connect REST Interface](https://docs.confluent.io/platform/7.9/connect/references/restapi.html)

실습 후 아래 명령으로 Datagen의 추가 발행을 멈춘다. 이미 기록된 Avro 토픽의 데이터는 48번의 색인 예제에서 읽을 수 있다. [Confluent · DROP CONNECTOR](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/drop-connector.html)

```sql
DROP CONNECTOR clickstream_json_47;
DROP CONNECTOR clickstream_avro_47;
```
