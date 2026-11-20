# Building and Operating Kafka Connect Pipelines

Kafka Connect는 외부 시스템과 Kafka 토픽 사이에서 데이터를 지속적으로 옮기는 런타임이다. 커넥터의 설정으로 데이터 경로를 정의하고, 워커가 작업 배치, 오프셋 저장, 상태 조회를 관리한다. [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

## 1. 소스, 싱크, 워커의 역할

| 구성 요소 | 역할 |
| --- | --- |
| 소스 커넥터 | 파일, 데이터베이스, 외부 API의 데이터를 Kafka 토픽으로 가져온다. |
| 싱크 커넥터 | Kafka 토픽의 레코드를 읽어 파일, DB, 검색 엔진에 기록한다. |
| `Connector` | 설정을 검증하고, 입력 파일이나 외부 파티션을 어떻게 나눌지 정해 각 작업의 설정을 생성한다. |
| `Task` | 배정된 데이터를 읽거나 쓰는 작업 단위다. 기본적으로 `tasks.max`가 작업 개수의 상한이다. 커넥터가 실제로 나눌 수 있는 단위에 따라 작업이 더 적게 생성될 수 있다. |
| 워커 | 커넥터와 작업을 실행하는 프로세스다. 분산 모드에서는 워커 그룹이 담당 작업을 나눈다. |

Converter는 Kafka의 키·값 바이트와 Connect 내부의 값·스키마 사이를 변환한다. SMT(Single Message Transform)는 연결 경로에서 레코드 하나씩 필드 추가, 토픽 라우팅 같은 가벼운 변환을 수행한다. 데이터 경로와 직렬화 형식은 `connector.class`, Converter, 입력·출력 토픽 설정을 함께 보고 확인한다. [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Apache Kafka · Connector Development Guide](https://kafka.apache.org/43/kafka-connect/connector-development-guide/)

## 2. 단일 모드와 분산 모드

| 항목 | 단일 모드 | 분산 모드 |
| --- | --- | --- |
| 시작 명령 | `connect-standalone.sh worker.properties connector.properties` | `connect-distributed.sh worker.properties` |
| 작업 배치 | 한 워커 프로세스에서 실행한다. | 같은 `group.id`의 워커에서 작업을 배정한다. 워커가 떠나면 남은 워커로 재배정할 수 있다. |
| 설정 등록 | 실행 인자로 커넥터 설정을 넘기거나 REST API를 사용한다. | REST API에서 커넥터 설정을 등록한다. |
| 상태 보관 | 소스 오프셋을 `offset.storage.file.filename` 파일에 저장한다. | 커넥터·작업 설정, 소스 오프셋, 상태를 Kafka 내부 토픽에 저장한다. |

분산 워커는 같은 `group.id`와 내부 토픽 세 개를 공유한다. 같은 Kafka 클러스터에서 여러 Connect 클러스터를 운영할 때는 그룹 ID와 내부 토픽 이름을 모두 다르게 지정한다. 내부 토픽은 압축 정책 `cleanup.policy=compact`를 사용하고 복제 계수를 환경에 맞게 정한다. `config.storage.topic`은 설정 순서를 유지하도록 파티션 하나를 사용한다. `offset.storage.topic`은 기본 소스 오프셋, `status.storage.topic`은 커넥터와 작업 상태를 저장한다. 싱크의 Kafka 소비 위치는 싱크 컨슈머 그룹 오프셋에 저장된다. [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Apache Kafka · Connect Administration](https://kafka.apache.org/43/kafka-connect/administration/)

## 3. 커스텀 커넥터 설계

커넥터의 `start()`는 설정을 읽고, `taskClass()`는 워커가 생성할 클래스, `taskConfigs(maxTasks)`는 각 작업의 설정을 반환한다. 예를 들어 여러 파일을 읽는 소스라면 작업 설정별로 겹치지 않는 파일을 배정한다. 외부 데이터의 분할 기준과 재시작 위치를 함께 설계해야 워커 간 재배정 뒤에도 이어서 처리할 수 있다. [Apache Kafka · Connector Development Guide](https://kafka.apache.org/43/kafka-connect/connector-development-guide/)

- **소스 작업**은 `SourceTask.poll()`로 외부 데이터를 읽어 `SourceRecord` 목록을 반환한다. 각 레코드에 외부 데이터의 위치를 나타내는 `sourcePartition`과 진행 지점인 `sourceOffset`을 설정한다. 예를 들어 파일 경로를 파티션 식별자로, 읽은 바이트 위치를 오프셋으로 사용할 수 있다. 재시작할 때는 `context.offsetStorageReader()`로 저장한 위치를 조회한다.
- **싱크 작업**은 `SinkTask.put()`에서 `SinkRecord`를 받아 목적지에 기록한다. 버퍼링한다면 오프셋이 커밋되기 전에 `flush()`에서 아직 남은 데이터를 보내고 목적지의 기록 완료를 확인한다. 기본 `preCommit()`은 `flush()`를 호출한다. 직접 구현할 때는 기록을 마친 범위만 안전한 오프셋으로 반환한다. 목적지 기록과 오프셋 커밋 사이의 장애로 같은 레코드가 다시 전달될 수 있으므로 이벤트 ID를 기준으로 중복 반영을 제어한다. [Apache Kafka · Connector Development Guide](https://kafka.apache.org/43/kafka-connect/connector-development-guide/) · [Apache Kafka · SinkTask API](https://kafka.apache.org/43/javadoc/org/apache/kafka/connect/sink/SinkTask.html)

`ConfigDef`에서 이름, 타입, 기본값, 검증 규칙, 설명을 정의하고 `config()`에서 반환한다. `Importance.HIGH`는 접속 주소나 대상처럼 사용자가 먼저 확인해야 하는 옵션, `MEDIUM`은 운영 조건에 맞춰 조정하는 옵션, `LOW`는 기본값을 주로 쓰는 세부 옵션에 적용할 수 있다. 필수 여부는 기본값 유무로, 값의 유효성은 검증 규칙으로 별도로 나타낸다. 아래 예시에서 `source.endpoint`는 필수이며 null과 빈 문자열을 거부하고, `batch.size`는 기본값이 `500`이며 1 이상이어야 한다. [Apache Kafka · ConfigDef API](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/config/ConfigDef.html)

```java
return new ConfigDef()
        .define("source.endpoint", ConfigDef.Type.STRING, ConfigDef.NO_DEFAULT_VALUE,
                ConfigDef.CompositeValidator.of(new ConfigDef.NonNullValidator(),
                        new ConfigDef.NonEmptyString()), ConfigDef.Importance.HIGH,
                "Endpoint from which the source task reads records")
        .define("batch.size", ConfigDef.Type.INT, 500, ConfigDef.Range.atLeast(1),
                ConfigDef.Importance.MEDIUM, "Maximum number of records per poll");
```

플러그인은 의존성과 함께 배포하고, 작업을 맡을 수 있는 모든 워커에서 같은 버전을 발견할 수 있도록 `plugin.path`를 구성한다. 워커 시작 후 `GET /connector-plugins`로 설치 상태를 확인한다. 이 응답은 요청에 응답한 워커의 플러그인 목록이므로 롤링 배포 중에는 워커별로 확인한다. [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

## 4. Docker에서 분산 워커 실행하기

01번의 Kafka 4.3.2 `compose.yaml`과 같은 디렉터리에 `compose.connect.yaml`을 만든다. 워커는 Kafka에 `kafka:29092`로 접속하고, 호스트에서는 `127.0.0.1:18083`의 REST API를 사용한다. 소스와 싱크는 Kafka 배포본의 FileStream 플러그인을 사용한다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기) · [Apache Kafka · Connect Quick Start](https://kafka.apache.org/43/getting-started/quickstart/)

```yaml
services:
  connect:
    image: apache/kafka:4.3.2
    depends_on:
      kafka:
        condition: service_healthy
    entrypoint: ["/opt/kafka/bin/connect-distributed.sh"]
    command: ["/etc/kafka-connect/worker.properties"]
    ports:
      - "127.0.0.1:18083:8083"
    volumes:
      - "./connect-worker.properties:/etc/kafka-connect/worker.properties:ro"
```

아래를 `connect-worker.properties`로 저장한다. 내부 토픽의 복제 계수와 파티션 수는 단일 브로커 실습에 맞춘 값이다.

```properties
bootstrap.servers=kafka:29092
group.id=connect-file-demo
listeners=http://0.0.0.0:8083
rest.advertised.host.name=connect

config.storage.topic=connect-file-demo-configs
config.storage.replication.factor=1
offset.storage.topic=connect-file-demo-offsets
offset.storage.replication.factor=1
offset.storage.partitions=1
status.storage.topic=connect-file-demo-status
status.storage.replication.factor=1
status.storage.partitions=1

key.converter=org.apache.kafka.connect.storage.StringConverter
value.converter=org.apache.kafka.connect.storage.StringConverter
plugin.path=/opt/kafka/libs/connect-file-4.3.2.jar
```

새 실습 환경에서 워커를 시작하고 토픽과 입력 파일을 만든다. 파일 경로는 Connect 컨테이너 안의 경로다.

```bash
connect_compose() {
  docker compose -f compose.yaml -f compose.connect.yaml "$@"
}

connect_compose up -d
connect_url=http://127.0.0.1:18083
curl -fsS --retry 20 --retry-all-errors --retry-delay 1 "$connect_url/connector-plugins"

connect_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic connect-file-demo-data \
  --partitions 1 --replication-factor 1

printf '%s\n' 'order-901 created' 'order-902 paid' |
  connect_compose exec -T connect sh -c 'cat > /tmp/connect-input.txt'
```

같은 셸에서 싱크와 소스 순으로 등록한다. 커넥터 설정의 `PUT` 요청은 경로에 이름을 지정하고 본문에는 설정 객체를 전달한다.

```bash
curl -fsS -X PUT -H 'Content-Type: application/json' \
  "$connect_url/connectors/file-sink/config" -d '{
    "connector.class": "FileStreamSinkConnector",
    "tasks.max": "1",
    "topics": "connect-file-demo-data",
    "file": "/tmp/connect-output.txt"
  }'

curl -fsS -X PUT -H 'Content-Type: application/json' \
  "$connect_url/connectors/file-source/config" -d '{
    "connector.class": "FileStreamSourceConnector",
    "tasks.max": "1",
    "topic": "connect-file-demo-data",
    "file": "/tmp/connect-input.txt"
  }'

connect_compose exec -T connect sh -ec '
  attempts=0
  until grep -q "^order-902 paid$" /tmp/connect-output.txt 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
      echo "Timed out waiting for connector output" >&2
      exit 1
    fi
    sleep 1
  done
  cat /tmp/connect-output.txt
'
curl -fsS "$connect_url/connectors/file-source/status"
curl -fsS "$connect_url/connectors/file-sink/status"
```

각 `status` 응답에서 커넥터와 작업이 `RUNNING`인지 확인한다. 시작 직후에는 작업 배정과 파일 기록까지 잠시 걸릴 수 있다. 입력 파일의 두 줄이 출력 파일까지 전달됐는지 확인하고, 입력 파일에 새 줄을 추가하면 커넥터를 다시 등록하지 않아도 전달된다. 이 실습의 로컬 파일은 워커 컨테이너에 속한다. 여러 워커에 걸쳐 실행할 커넥터는 작업이 옮겨간 워커에서도 원본과 목적지에 접근할 수 있어야 한다. [Apache Kafka · Connect Administration](https://kafka.apache.org/43/kafka-connect/administration/)

Kafka 4.3.2에서 소스와 싱크 커넥터 및 각 작업이 모두 `RUNNING`으로 조회됐다. 입력 파일에 추가한 `order-903 shipped`까지 총 세 줄이 Kafka 토픽과 출력 파일에 기록됐다.

## 5. REST API와 웹 화면으로 운영하기

| 작업 | REST API |
| --- | --- |
| 설치된 커넥터 종류 확인 | `GET /connector-plugins` |
| 등록된 커넥터와 작업 확인 | `GET /connectors`, `GET /connectors/{name}/status` |
| 설정 조회와 수정 | `GET /connectors/{name}/config`, `PUT /connectors/{name}/config` |
| 처리 일시 중지와 재개 | `PUT /connectors/{name}/pause`, `PUT /connectors/{name}/resume` |
| 실패한 커넥터·작업 재시작 | `POST /connectors/{name}/restart?includeTasks=true&onlyFailed=true` |

커넥터가 `RUNNING`이어도 개별 작업에 `FAILED`가 나타날 수 있다. `status`에서 작업 상태와 오류, 할당된 워커를 확인하고, 해당 워커 로그에서 원인을 찾은 뒤 재시작한다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [Apache Kafka · Connect Administration](https://kafka.apache.org/43/kafka-connect/administration/)

브라우저 운영 도구의 예로 Kafbat UI가 있다. 같은 Compose 네트워크에서 실행할 경우 `KAFKA_CLUSTERS_0_KAFKACONNECT_0_ADDRESS`에 `http://connect:8083`을 지정한다. 화면에서 커넥터 목록과 설정, 작업 상태를 확인하며 조회·설정 변경·재시작 권한은 역할별로 나눌 수 있다. [Kafbat UI · Configuration Properties](https://ui.docs.kafbat.io/configuration/misc-configuration-properties) · [Kafbat UI · Role-Based Access Control](https://ui.docs.kafbat.io/configuration/rbac-role-based-access-control)
