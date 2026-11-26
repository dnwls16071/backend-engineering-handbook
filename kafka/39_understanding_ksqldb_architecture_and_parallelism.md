# Understanding ksqlDB Architecture and Parallelism

ksqlDB는 Kafka 토픽을 읽고 쓰는 스트림 처리 애플리케이션을 SQL로 정의한다. 서버의 엔진은 SQL에서 Kafka Streams 토폴로지를 만들고, 입력 레코드가 도착할 때마다 결과를 갱신한다. CLI와 애플리케이션은 REST API를 통해 서버에 접속한다. [Confluent · ksqlDB Architecture](https://docs.confluent.io/platform/current/ksqldb/operate-and-deploy/how-it-works.html)

## 1. SQL에서 토폴로지까지

| 구성 요소 | 역할 |
| --- | --- |
| Kafka 브로커 | 입력과 출력 레코드, 쿼리 명령 및 상태 복구에 쓰는 내부 토픽을 보관한다. |
| ksqlDB 서버 프로세스 | REST 요청을 받고 SQL의 스키마와 구문을 검사한다. 지속 쿼리를 Kafka Streams 애플리케이션으로 실행한다. |
| Kafka Streams | 토폴로지의 파티션 할당, 오프셋 관리, 상태 저장, 재분배와 결과 발행을 맡는다. |
| ksqlDB CLI | 서버에 SQL을 보내고 결과를 표시한다. 지속 쿼리는 CLI 세션을 닫은 뒤에도 서버에서 실행된다. |

예를 들어 `CREATE STREAM ... AS SELECT`는 입력 레코드를 필터링하고 출력 토픽에 계속 발행한다. `CREATE TABLE ... AS SELECT`로 고객별 주문 건수를 정의하면 새 이벤트마다 해당 고객의 이전 건수를 찾아 갱신한다. `SELECT`로 열을 고르거나 `WHERE`로 한 행을 거르는 로직은 각 레코드만으로 계산할 수 있다. 집계와 조인은 이전 레코드에서 얻은 상태를 보관하며, RocksDB가 태스크의 로컬 상태 저장소를 제공한다. 상태에 연결된 Kafka changelog를 다시 읽으면 장애로 다른 서버에 배치된 태스크가 상태를 복원할 수 있다. [Confluent · Performance Guidelines](https://docs.confluent.io/platform/7.9/ksqldb/operate-and-deploy/performance-guidelines.html) · [Confluent · Kafka Streams Architecture](https://docs.confluent.io/platform/7.9/streams/architecture.html)

대화형 모드에서 같은 `ksql.service.id`를 쓰는 서버는 Kafka의 명령 토픽을 공유한다. 서버마다 명령 토픽을 읽어 같은 지속 쿼리를 구성하고 입력 파티션을 나누어 처리한다. Headless 모드는 배포할 SQL 파일을 서버에 지정한다. 같은 ksqlDB 클러스터에 속한 서버는 동일한 모드를 사용한다. [Confluent · Deployment Modes](https://docs.confluent.io/platform/current/ksqldb/operate-and-deploy/how-it-works.html)

## 2. 프로세스, 스레드, 태스크

| 실행 단위 | 병렬 처리에서 하는 일 |
| --- | --- |
| 서버 프로세스 | 지속 쿼리를 실행하는 Kafka Streams 인스턴스를 올린다. 서버를 늘리면 그 쿼리의 태스크를 다른 프로세스에도 배치할 수 있다. |
| 스트림 스레드 | 한 개 이상의 태스크를 실행한다. 서버 설정 `ksql.streams.num.stream.threads`가 애플리케이션 인스턴스당 스트림 스레드 수를 정한다. |
| 스트림 태스크 | 토폴로지의 해당 부분에서 입력 파티션을 처리하는 단위다. 한 시점에 한 스트림 스레드가 활성 태스크를 맡고, 상태가 필요한 연산은 해당 태스크의 저장소를 쓴다. |

입력이 파티션 6개인 단순한 지속 쿼리는 활성 태스크 6개를 갖는다. 서버 2대에 쿼리당 스트림 스레드를 2개씩 두면 최대 4개 스레드가 동시에 태스크를 실행하고, 일부 스레드는 태스크를 여러 개 맡는다. 서버 4대에 스레드를 2개씩 두면 활성 태스크를 맡을 수 있는 스레드는 최대 6개다. 조인에서는 태스크 하나가 여러 입력 토픽의 같은 번호 파티션들을 맡을 수 있고, 재분배 뒤에는 별도의 서브토폴로지에 태스크가 생긴다. [Confluent · Kafka Streams Architecture](https://docs.confluent.io/platform/7.9/streams/architecture.html) · [Confluent · Server Configuration](https://docs.confluent.io/platform/7.9/ksqldb/reference/server-configuration.html#ksql-streams-num-stream-threads)

지속 쿼리의 처리량을 판단할 때는 입력 파티션 수와 파티션별 lag를 함께 본다. 특정 키에 이벤트가 몰리면 해당 키가 있는 파티션에 작업이 집중된다. 상태를 쓰는 쿼리에서는 파티션을 늘릴 때 RocksDB 저장소 수와 메모리·디스크 비용도 함께 증가할 수 있다. [Confluent · Capacity Planning](https://docs.confluent.io/platform/7.9/ksqldb/operate-and-deploy/capacity-planning.html)

## 3. 기존 Kafka에 서버와 CLI 연결

Confluent Platform `7.9.11`의 서버와 CLI 이미지를 같은 태그로 사용한다. 이 구성은 이미 실행 중인 PLAINTEXT Kafka 브로커에 연결한다. 예를 들어 01번 단일 브로커 실습의 `compose.yaml` 디렉터리에서 `docker compose -p kafka-lab up -d --wait kafka`로 브로커를 시작하면 기본 네트워크는 `kafka-lab_default`, 컨테이너용 주소는 `kafka:29092`다. 다른 클러스터를 사용하면 `KSQL_LAB_NETWORK`와 `KSQL_LAB_BOOTSTRAP`을 해당 환경에 맞춘다. 서버 컨테이너에서 브로커가 광고하는 주소에도 접근할 수 있어야 한다. 브로커부터 함께 구성할 때는 Confluent Quick Start의 동일 버전 예제를 사용할 수 있다. [01번 Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기) · [Confluent · ksqlDB Quick Start](https://docs.confluent.io/platform/7.9/ksqldb/quickstart.html)

아래 내용을 `compose.ksqldb.yaml`로 저장한다. REST API는 호스트의 `127.0.0.1:18088`과 Compose 네트워크의 `ksqldb:8088`에서 접속할 수 있다. 내부 토픽 복제 계수는 단일 브로커에서도 동작하도록 `1`을 사용한다. [Confluent · ksqlDB Docker Installation](https://docs.confluent.io/platform/7.9/ksqldb/operate-and-deploy/installation/install-ksqldb-with-docker.html)

```yaml
services:
  ksqldb:
    image: confluentinc/cp-ksqldb-server:7.9.11
    hostname: ksqldb
    ports: ["127.0.0.1:18088:8088"]
    environment:
      KSQL_BOOTSTRAP_SERVERS: "${KSQL_LAB_BOOTSTRAP:-kafka:29092}"
      KSQL_HOST_NAME: ksqldb
      KSQL_LISTENERS: http://0.0.0.0:8088
      KSQL_KSQL_SERVICE_ID: backend_engineering_handbook_ksql_
      KSQL_KSQL_INTERNAL_TOPIC_REPLICAS: "1"
      KSQL_KSQL_STREAMS_REPLICATION_FACTOR: "1"
      KSQL_KSQL_STREAMS_NUM_STREAM_THREADS: "2"
    networks: [kafka-lab]

  ksql-cli:
    image: confluentinc/cp-ksqldb-cli:7.9.11
    entrypoint: ["ksql", "http://ksqldb:8088"]
    networks: [kafka-lab]

networks:
  kafka-lab:
    external: true
    name: "${KSQL_LAB_NETWORK:-kafka-lab_default}"
```

```bash
docker compose -f compose.ksqldb.yaml up -d ksqldb
curl --retry 30 --retry-delay 1 --retry-all-errors -fsS http://127.0.0.1:18088/info
docker compose -f compose.ksqldb.yaml run --rm ksql-cli
```

CLI의 `ksql>` 프롬프트에서 다음 명령을 실행한다. `SHOW TOPICS`에서 Kafka 토픽 목록을 확인하고, `SHOW QUERIES`에서 실행 중인 지속 쿼리를 확인한다. 처음 시작한 실습 클러스터에는 사용자 쿼리가 없다. [Confluent · Quick Reference](https://docs.confluent.io/platform/7.9/ksqldb/developer-guide/ksqldb-reference/quick-reference.html)

```sql
SHOW TOPICS;
SHOW STREAMS;
SHOW QUERIES;
```
