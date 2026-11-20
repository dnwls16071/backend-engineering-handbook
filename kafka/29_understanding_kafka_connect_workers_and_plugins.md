# Understanding Kafka Connect Workers and Plugins

Kafka Connect는 외부 데이터와 Kafka 토픽 사이의 전송을 플러그인으로 실행한다. 파일을 읽으려면 소스 커넥터를, Kafka의 레코드를 데이터베이스에 쓰려면 싱크 커넥터를 등록한다. 분산 워커를 설치해 소스와 싱크를 연결하는 실행 명령은 08번에 있다. 이 편에서는 플러그인을 설치한 뒤 어떤 구성 요소가 실제 데이터를 처리하는지 살펴본다. [08번 Connect 파이프라인](08_building_and_operating_kafka_connect_pipelines.md) · [Apache Kafka · Connect Overview](https://kafka.apache.org/43/kafka-connect/overview/)

## 1. 플러그인과 실행 단위를 구분한다

| 구성 요소 | 맡는 일 |
| --- | --- |
| Connector | 외부 시스템 연결 설정을 검증하고 작업에 전달할 구성을 만든다. |
| Task | 외부 시스템의 일부를 실제로 읽거나 쓴다. `tasks.max`는 기본적으로 생성할 작업 수의 상한이며, 커넥터가 분할 가능한 단위가 적으면 실제 작업 수는 더 적다. |
| Worker | Connector와 Task를 실행하는 프로세스다. |
| Connect Cluster | 같은 `group.id`와 내부 토픽을 사용하는 분산 워커 집합이다. 워커가 추가되거나 빠지면 작업을 다시 배정한다. |

소스 방향에서는 `SourceTask`가 Connect 레코드를 만들고, SMT가 레코드의 키·값·토픽 같은 속성을 바꾼 뒤 Converter가 Kafka에 넣을 바이트로 변환한다. 싱크 방향에서는 Converter가 바이트를 Connect 레코드로 읽고, SMT를 거친 레코드를 `SinkTask`로 전달한다. 필드 추출과 토픽 변경은 SMT, JSON·Avro 표현 선택은 Converter의 역할이다. 키와 값에는 별도 Converter를 지정할 수 있다. [Apache Kafka · Connector Development Guide](https://kafka.apache.org/43/kafka-connect/connector-development-guide/) · [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

## 2. 플러그인 배포와 기동 순서

Confluent Marketplace에서 파일·JDBC·CDC 커넥터를 비교할 때는 소스/싱크 방향, 대상 시스템과 지원 버전, 라이선스, 추가 JDBC 드라이버 유무를 확인한다. 예를 들어 파일을 모아 읽는 SpoolDir, SQL로 폴링하는 JDBC Source, 변경 로그를 읽는 Debezium은 모두 소스 플러그인이지만 입력과 재시작 위치가 서로 다르다. 내려받은 패키지는 버전과 의존성을 확인해 `plugin.path` 아래 다른 플러그인과 분리된 디렉터리에 배치한다. [Confluent · Marketplace](https://www.confluent.io/hub/) · [Apache Kafka · Plugin Discovery](https://kafka.apache.org/43/kafka-connect/user-guide/#plugin-discovery)

단일 모드는 `connect-standalone.sh`를 실행하고 소스 위치를 로컬 오프셋 파일에 보관한다. 분산 모드는 `connect-distributed.sh`를 실행한 뒤 REST API로 커넥터를 등록한다. 플러그인 추가 후에는 작업을 맡을 모든 워커에 같은 버전을 설치하고 각 워커를 재시작한다. `GET /connector-plugins`는 응답한 워커의 발견 결과이므로 여러 워커에서 같은 결과가 나오는지 확인한다. [Apache Kafka · Running Kafka Connect](https://kafka.apache.org/43/kafka-connect/user-guide/#running-kafka-connect)

## 3. 등록 이후에 확인할 것

분산 워커는 설정을 `config.storage.topic`, 기본 소스 진행 위치를 `offset.storage.topic`, 커넥터와 작업 상태를 `status.storage.topic`에 기록한다. 설정 토픽은 한 파티션을 쓰며 세 토픽은 모두 컴팩션을 사용한다. 싱크가 Kafka에서 어디까지 읽었는지는 해당 싱크의 소비자 그룹 오프셋으로 확인한다. [Apache Kafka · Running Kafka Connect](https://kafka.apache.org/43/kafka-connect/user-guide/#running-kafka-connect)

08번의 실습 워커가 호스트의 `18083` 포트에서 실행 중이라면 아래에서 버전, 플러그인, 설정 정의를 확인한다. `file-source`까지 등록했다면 커넥터 상태와 각 작업 상태를 따로 읽는다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)

```bash
connect_url=http://127.0.0.1:18083
plugin=org.apache.kafka.connect.file.FileStreamSourceConnector

curl -fsS "$connect_url/"
curl -fsS "$connect_url/connector-plugins" |
  jq --arg plugin "$plugin" '.[] | select(.class == $plugin)'
curl -fsS "$connect_url/connector-plugins/$plugin/config" | jq 'map(.name)'
curl -fsS "$connect_url/connectors/file-source/status" |
  jq '{connector: .connector.state, tasks: [.tasks[] | {id, state, worker_id}]}'
```

Kafka Connect 4.3.2에서 FileStream 소스 플러그인, 설정 정의의 `file`·`topic` 항목, 커넥터와 작업의 `RUNNING` 상태를 확인했다.

HTTP 등록이 성공해도 외부 시스템 인증이나 입력 파일 접근에 실패하면 Task가 `FAILED`가 될 수 있다. 플러그인 발견, 설정·작업 생성, 데이터 흐름을 순서대로 확인하면 문제가 어느 단계에 있는지 알 수 있다. 다음 편은 이 절차로 SpoolDir를 등록하고 파일 처리 위치를 확인한다. [SpoolDir CSV 실습](30_ingesting_csv_files_with_kafka_connect_spooldir.md) · [Apache Kafka · Connect Administration](https://kafka.apache.org/43/kafka-connect/administration/)
