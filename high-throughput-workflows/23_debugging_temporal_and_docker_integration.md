# Debugging Temporal and Docker Integration

장애를 Connect·Kafka 전달, Temporal 시작, Worker 폴링, Activity 순으로 나눠 조사한다. 각 경계에서 다음 단계로 넘긴 증거를 확인한다. [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Temporal CLI · Workflow](https://docs.temporal.io/cli/command-reference/workflow) · [Docker Compose · Logs](https://docs.docker.com/reference/cli/docker/compose/logs/)

## 1. Docker와 Kafka 연결부터 확인한다

| 증상 | 먼저 확인할 것 | 근거 |
| --- | --- | --- |
| Connect가 플러그인이나 DB에 연결하지 못함 | docker compose ps, logs connect-cdc, Connect 태스크 상태, 컨테이너 DNS와 포트 | [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/) · [Docker Compose · Logs](https://docs.docker.com/reference/cli/docker/compose/logs/) · [Apache Kafka 4.3 · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/) |
| 호스트 앱이 Kafka에 도달하지 못함 | 부트스트랩 주소와 이후 브로커가 알려 주는 advertised listener가 둘 다 호스트에서 해석되는지 | [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/) · [Apache Kafka · Single-Broker Docker Compose](https://github.com/apache/kafka/blob/4.3.2/docker/examples/docker-compose-files/single-node/plaintext/docker-compose.yml) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) |
| Workflow는 있으나 작업이 시작되지 않음 | CLI 이력, namespace·Task Queue 일치, Worker 폴링 상태 | [Temporal · Task Queues](https://docs.temporal.io/task-queue) · [Temporal CLI · Workflow](https://docs.temporal.io/cli/command-reference/workflow) · [Temporal SDK 1.31.0 · WorkerFactory](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/worker/WorkerFactory.java) |
| Activity 실행이 반복 실패함 | 이력의 실패 원인과 시도 횟수, JDBC 연결 및 권한, Start-to-Close·전체 재시도 설정 | [Temporal Java · Activity Timeouts](https://docs.temporal.io/develop/java/activities/timeouts) · [Temporal CLI · Workflow](https://docs.temporal.io/cli/command-reference/workflow) · [Spring Boot 3.5 · Application Properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html) |

## 2. 관측 키를 연결해 복구한 결과를 확인한다

start-dev는 기본으로 인메모리 저장소를 사용한다. Worker 재시작을 검증할 때 개발 서버는 계속 켜 둔다. 개발 서버까지 재시작해 이력을 보존하려는 실험에는 --db-filename으로 로컬 저장 파일을 지정한다. [Temporal CLI · Server](https://docs.temporal.io/cli/command-reference/server) · [Temporal · Workflows](https://docs.temporal.io/workflows)

이벤트 ID로 Kafka 레코드와 Workflow ID를 연결하고, 주문 ID로 DB 처리 결과를 읽는다. 오프셋·워크플로우·처리 행을 확인하기 전에 데이터를 초기화하면 증거가 사라질 수 있다. 수정 후 동일 입력 재전달 시 업무 결과가 중복되지 않는지 확인한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [Temporal · Activities](https://docs.temporal.io/activities) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)
