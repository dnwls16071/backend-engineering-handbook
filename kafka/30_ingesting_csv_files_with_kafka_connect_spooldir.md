# Ingesting CSV Files with Kafka Connect SpoolDir

SpoolDir CSV Source Connector는 입력 디렉터리에서 완성된 CSV를 찾아 행마다 Kafka 레코드를 발행한다. 처리한 파일은 완료 경로로 옮긴다. 파일이 계속 자라는 환경의 Kafka 프로듀서는 23번에 있으며, 이 실습은 다 쓴 파일을 이름 변경으로 전달하는 방식이다. [Confluent · SpoolDir Connectors](https://docs.confluent.io/kafka-connectors/spooldir/current/index.html) · [파일 추가를 추적하는 Java 프로듀서](23_publishing_file_events_to_kafka.md)

## 1. 워커에 플러그인과 파일 경로를 준비한다

08번의 `compose.yaml`, `compose.connect.yaml`, `connect-worker.properties`를 새 실습 디렉터리에 준비한다. Confluent Marketplace의 `confluentinc/kafka-connect-spooldir` 패키지를 내려받아 `plugins/spooldir/` 아래 압축을 풀고, 플러그인 JAR와 동봉된 의존성을 함께 둔다. Marketplace의 2.0.72 릴리스와 사용 중인 워커의 지원 범위를 확인한다. `connect-worker.properties`의 기존 `plugin.path` 값에 `,/opt/connect-plugins`를 추가한다. [08번 FileStream 실습](08_building_and_operating_kafka_connect_pipelines.md#4-docker에서-분산-워커-실행하기) · [Confluent Marketplace · Kafka Connect Spooldir](https://www.confluent.io/hub/confluentinc/kafka-connect-spooldir) · [Apache Kafka · Plugin Discovery](https://kafka.apache.org/43/kafka-connect/user-guide/#plugin-discovery)

`compose.spool.yaml`을 추가한다. 여러 워커가 하나의 커넥터를 실행할 수 있는 구성에서는 작업을 받은 워커가 입력·완료·오류 경로와 같은 파일을 볼 수 있어야 한다. 이 예시는 워커 하나로 진행한다. [Confluent · CSV Source Connector](https://docs.confluent.io/kafka-connectors/spooldir/current/connectors/csv_source_connector.html)

```yaml
services:
  connect:
    volumes:
      - ./plugins:/opt/connect-plugins:ro
      - ./spool:/var/spool/connect-lab
```

```bash
spool_compose() {
  docker compose -f compose.yaml -f compose.connect.yaml -f compose.spool.yaml "$@"
}
mkdir -p spool/in spool/finished spool/error
spool_compose up -d

connect_url=http://127.0.0.1:18083
connector_class=com.github.jcustenborder.kafka.connect.spooldir.SpoolDirCsvSourceConnector
curl -fsS --retry 20 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins" |
  jq -e --arg class "$connector_class" 'any(.[]; .class == $class)'

spool_compose exec -T connect sh -ec '
  for d in in finished error; do
    test -w "/var/spool/connect-lab/$d"
  done
'
spool_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic orders.spool.csv.v1 \
  --partitions 1 --replication-factor 1

printf '%s\n' 'id,status' 'p-101,CREATED' 'p-102,PAID' > spool/in/orders-001.csv.part
mv spool/in/orders-001.csv.part spool/in/orders-001.csv
```

확장자가 `.part`인 상태에서 파일을 완성한 뒤 같은 디렉터리에서 이름을 바꾼다. 아래 `input.file.pattern`은 완성된 파일 이름만 선택한다. 중간에 워커가 멈추면 처리 중 표시가 붙은 파일과 저장된 오프셋을 먼저 확인하고, 입력 파일과 Connect 내부 토픽 데이터를 보존한 상태에서 작업을 재개한다. [Confluent · File System Configuration](https://docs.confluent.io/kafka-connectors/spooldir/current/connectors/csv_source_connector.html)

## 2. Converter와 SMT가 포함된 CSV Source 등록

아래를 `spooldir-csv.json`으로 저장한다. CSV 헤더에서 필드와 키 스키마를 생성하고 `id`를 키 필드로 선택한다. `InsertField$Value`는 값에 출처 필드를 추가한다. `JsonConverter`의 `schemas.enable=true`가 결과를 `schema`와 `payload`가 있는 JSON으로 저장한다. [Confluent · CSV Schema Generation](https://docs.confluent.io/kafka-connectors/spooldir/current/connectors/csv_source_connector.html) · [Apache Kafka · Connect Transformations](https://kafka.apache.org/43/kafka-connect/user-guide/#transformations)

```json
{
  "name": "orders-csv-source",
  "connector.class": "com.github.jcustenborder.kafka.connect.spooldir.SpoolDirCsvSourceConnector",
  "tasks.max": "1",
  "topic": "orders.spool.csv.v1",
  "input.path": "/var/spool/connect-lab/in",
  "finished.path": "/var/spool/connect-lab/finished",
  "error.path": "/var/spool/connect-lab/error",
  "input.file.pattern": "orders-.*[.]csv",
  "cleanup.policy": "MOVE",
  "halt.on.error": "true",
  "csv.first.row.as.header": "true",
  "schema.generation.enabled": "true",
  "schema.generation.key.fields": "id",
  "schema.generation.key.name": "study.spool.OrderKey",
  "schema.generation.value.name": "study.spool.OrderValue",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "true",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "true",
  "transforms": "origin",
  "transforms.origin.type": "org.apache.kafka.connect.transforms.InsertField$Value",
  "transforms.origin.static.field": "origin",
  "transforms.origin.static.value": "csv-spool"
}
```

실습에 HTTPie, `jq`, `kcat`을 사용한다. `kcat`은 예전 강의에서 `kafkacat`으로 부르던 도구다. HTTPie의 `http`로 설정을 검증하고, `error_count`가 0인 경우 등록한다. `RUNNING` 상태가 표시된 뒤 Kafka에 레코드가 도착했는지, CSV가 완료 경로에 있는지 확인한다. [HTTPie · Redirected Input](https://httpie.io/docs/cli/redirected-input) · [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [kcat · README](https://github.com/edenhill/kcat)

```bash
http --check-status PUT "$connect_url/connector-plugins/$connector_class/config/validate" \
  Content-Type:application/json < spooldir-csv.json | jq -e '.error_count == 0' &&
  http --check-status PUT "$connect_url/connectors/orders-csv-source/config" \
    Content-Type:application/json < spooldir-csv.json
http --check-status GET "$connect_url/connectors/orders-csv-source/status"

kcat -b localhost:19092 -L -t orders.spool.csv.v1
kcat -b localhost:19092 -C -t orders.spool.csv.v1 -p 0 -o beginning -c 2 -e |
  jq -c '.payload | {id, status, origin}'
ls -l spool/finished
```

## 3. 파일 진행 위치와 재처리 범위

소스의 오프셋은 프로듀서가 쓰는 Kafka 파티션 오프셋과 별개다. 소스는 커넥터가 정의한 `sourcePartition`과 `sourceOffset`으로 원본 파일의 진행 위치를 관리한다. 분산 워커는 이를 기본 소스 오프셋 토픽에 저장한다. 데이터가 Kafka에서 보여도 아직 다음 오프셋 저장 주기가 지나지 않았을 수 있다. 상태, 등록 설정, 실제 Kafka 레코드와 함께 `GET /connectors/orders-csv-source/offsets` 결과를 비교한다. [Apache Kafka · Connector Development Guide](https://kafka.apache.org/43/kafka-connect/connector-development-guide/) · [Apache Kafka · Connect Configuration](https://kafka.apache.org/43/configuration/kafka-connect-configs/)

같은 파일을 처음부터 다시 읽으려면 **실습 커넥터 하나만** 대상으로 한다. `stop`을 요청하고 상태가 `STOPPED`인 것을 확인한 뒤 오프셋을 조회하고 초기화한다. 필요한 경우 `PATCH /offsets`로 조회 결과의 원본 파티션 중 하나를 지정할 수 있고, `offset: null`은 그 파티션의 위치를 초기화한다. 아래 `DELETE /offsets`는 해당 커넥터의 모든 위치에 적용된다. [Apache Kafka · Connect Offsets API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)

```bash
http --check-status PUT "$connect_url/connectors/orders-csv-source/stop"
http --check-status GET "$connect_url/connectors/orders-csv-source/status"
http --check-status GET "$connect_url/connectors/orders-csv-source/offsets"
```

`STOPPED`를 확인한 뒤 아래를 실행한다. 완료 경로로 옮긴 파일을 입력에 되돌려야 다시 읽을 수 있다. 재처리는 Kafka에 새 레코드를 발행하므로 다운스트림에서 중복을 고려한다. kcat은 데이터 토픽 조회에 사용하고, 이 실습의 소스 위치 변경은 Connect REST API로 처리한다. [Apache Kafka · Connect Offsets API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)

```bash
http --check-status DELETE "$connect_url/connectors/orders-csv-source/offsets"
mv spool/finished/orders-001.csv spool/in/orders-001.csv
http --check-status PUT "$connect_url/connectors/orders-csv-source/resume"
```

Kafka Connect 4.3.2의 FileStream 소스로 정지·초기화·재개 절차를 확인했다. 대상 소스의 레코드는 재발행됐고, 같은 워커의 다른 소스 오프셋은 유지됐다.
