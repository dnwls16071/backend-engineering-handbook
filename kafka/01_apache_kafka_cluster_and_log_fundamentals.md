# Apache Kafka Cluster and Log Fundamentals

Kafka의 브로커가 토픽을 어떻게 저장하고 복제하는지, 클라이언트가 어느 브로커에 연결하는지 정리한다. Docker 실습은 Apache Kafka 4.3.2와 KRaft를 사용한다. [Apache Kafka · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka · Docker](https://kafka.apache.org/43/getting-started/docker/)

## 1. 생태계와 클러스터의 구성

| 구성 | 역할 |
| --- | --- |
| Broker | 파티션 로그를 저장하고 생산·소비 요청, 복제 트래픽을 처리한다. 하나 이상의 브로커가 클러스터를 이룬다. |
| Producer와 Consumer | Producer는 레코드를 발행하고, Consumer는 파티션별 오프셋부터 읽는다. 각 소비자 그룹은 읽기 위치를 따로 관리한다. |
| Kafka Connect | 커넥터를 실행해 외부 시스템과 Kafka 사이에서 데이터를 옮긴다. |
| Kafka Streams | Kafka의 데이터를 읽어 변환·집계하고 결과를 쓰는 애플리케이션 라이브러리다. |
| KRaft Controller | 컨트롤러 쿼럼으로 클러스터 메타데이터를 관리한다. 브로커 등록, 토픽·파티션 배치, 파티션 리더 변경을 조정한다. |

Kafka 3.x의 ZooKeeper 모드는 ZooKeeper로 클러스터 메타데이터와 컨트롤러 선출을 관리했다. Kafka 4.0부터는 ZooKeeper 모드가 제거됐으며 KRaft를 사용한다. 실습에서는 한 프로세스가 브로커와 컨트롤러를 함께 맡는다. 운영에서는 두 역할을 분리해 데이터 트래픽과 제어 쿼럼의 자원 및 장애 범위를 관리할 수 있다. [Apache Kafka · KRaft](https://kafka.apache.org/43/operations/kraft/) · [Kafka 4.0 Upgrade](https://kafka.apache.org/40/getting-started/upgrade/) · [Apache Kafka · Introduction](https://kafka.apache.org/43/getting-started/introduction/)

## 2. 토픽, 파티션, 레코드

- **토픽**은 이벤트의 이름과 보관·복제 정책을 정의한다. 예를 들어 `orders.lifecycle.v1`은 주문 상태 변경 이벤트라는 의미를 전달한다.
- **파티션**은 기록·복제·순서의 단위다. `topic + partition + offset`으로 레코드의 위치를 찾는다. 같은 오프셋 숫자가 서로 다른 파티션에 있을 수 있다.
- **레코드**에는 키, 값, 타임스탬프, 헤더가 있다. 브로커는 레코드를 기록할 때 파티션 내 오프셋을 할당한다. 헤더는 추적 ID처럼 본문 형식 밖의 메타데이터에 쓸 수 있다.

같은 주문의 이벤트를 한 파티션에서 읽으려면 주문 ID를 키로 사용하고, 생산자의 파티셔닝 방식과 파티션 개수를 고려한다. 파티션을 증설하면 이후 동일 키의 배치가 달라질 수 있다. 이름은 업무 영역과 이벤트 의미가 드러나게 짓고, 변경이 호환되지 않아 토픽을 분리해야 할 때 버전을 붙인다. 발행 서비스, 읽는 서비스, 키와 스키마, 보관 정책도 함께 기록한다. [Apache Kafka · Protocol and Metadata](https://kafka.apache.org/43/design/protocol/) · [Apache Kafka · Design](https://kafka.apache.org/43/design/design/)

## 3. 로그 세그먼트와 보관 정책

브로커는 파티션 로그를 세그먼트 파일들로 관리한다. 활성 세그먼트에 레코드 배치를 추가하고, 크기나 시간 조건이 충족되면 새 세그먼트로 전환한다. 오프셋 인덱스와 타임스탬프 인덱스를 이용해 조회할 위치를 찾는다. [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/)

| 설정 | 보관 동작 |
| --- | --- |
| `cleanup.policy=delete` | `retention.ms` 또는 파티션별 `retention.bytes`의 조건에 따라 오래된 세그먼트를 제거한다. |
| `cleanup.policy=compact` | 로그 클리너가 키별 최신 상태를 남긴다. 정리는 비동기이므로 이전 값이 잠시 보일 수 있다. |
| `cleanup.policy=compact,delete` | 남아 있는 로그에는 키별 정리를 적용하고, 기간이나 용량 한도를 넘은 오래된 세그먼트는 제거한다. |

`segment.bytes`와 `segment.ms`는 세그먼트를 전환하는 단위를 조정한다. 삭제는 세그먼트와 백그라운드 작업을 기준으로 일어나므로 레코드별로 정확한 만료 시각을 보장하는 데는 별도 설계가 필요하다. 컴팩션을 적용한 토픽에서 키가 있고 값이 `null`인 레코드는 삭제를 나타내는 tombstone이다. 이전 값과 tombstone이 정리된 뒤에도 남은 레코드의 오프셋은 유지되므로 번호가 건너뛸 수 있다. 이미 소비한 데이터도 보관 정책이 허용하는 기간에는 다시 읽을 수 있다. [Apache Kafka · Log Compaction](https://kafka.apache.org/43/design/design/) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/)

## 4. 복제, ISR, 생산자 확인

각 파티션은 리더와 팔로워 복제본을 가진다. 일반적인 생산 요청은 리더가 받고 팔로워는 리더의 로그를 가져온다. ISR은 리더를 포함한 동기 복제본 집합이다. 복제본이 뒤처지거나 복구되면 ISR 구성이 달라질 수 있다. [Apache Kafka · Replication](https://kafka.apache.org/43/design/design/)

복제 계수 3, `min.insync.replicas=2`, Producer의 `acks=all`을 기준으로 보면 다음과 같다.

| 현재 ISR | 쓰기 동작 |
| --- | --- |
| 3개 | `acks=all`은 현재 ISR의 복제를 기다린다. |
| 2개 | 최소 동기 복제본 수를 만족한다. |
| 1개 | 최소 조건을 충족하지 않아 `acks=all` 쓰기가 실패한다. |

복제 계수는 배치한 복제본 수이고 `min.insync.replicas`는 `acks=all` 쓰기를 허용할 최소 동기 복제본 수다. 실제 내구성과 쓰기 가용성을 판단할 때는 설정값과 현재 ISR을 함께 본다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/) · [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/)

## 5. 클라이언트가 브로커를 찾는 흐름

1. `bootstrap.servers`의 주소 중 하나로 연결해 클러스터의 토픽·파티션·브로커 메타데이터를 받는다.
2. 메타데이터에서 파티션 리더와 해당 브로커의 주소를 찾아 생산 요청을 보낸다. 리더가 바뀌면 메타데이터를 갱신한다.
3. 초기 연결 뒤 요청이 실패하면 브로커가 `advertised.listeners`로 알린 주소를 **클라이언트가 실행되는 네트워크**에서 해석하고 연결할 수 있는지 확인한다.

Docker 네트워크의 클라이언트는 서비스 이름 `kafka`에 연결할 수 있고, 호스트 클라이언트는 매핑한 호스트 포트를 사용한다. 브로커가 두 환경에 각자 접근 가능한 주소를 광고하도록 리스너를 나눈다. [Apache Kafka · Protocol](https://kafka.apache.org/43/design/protocol/) · [Apache Kafka · Listener Configuration](https://kafka.apache.org/43/security/listener-configuration/)

## 6. Docker에서 레코드와 복제 상태 확인하기

아래를 `compose.yaml`로 저장한다. 실습은 KRaft 단일 노드로 동작하며, 장애 전환을 검증하려면 여러 브로커에 복제본을 배치한 구성이 필요하다. [Apache Kafka · Docker](https://kafka.apache.org/43/getting-started/docker/)

```yaml
services:
  kafka:
    image: apache/kafka:4.3.2
    ports:
      - "127.0.0.1:19092:9092"
    environment:
      KAFKA_NODE_ID: "1"
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: "INTERNAL://:29092,HOST://:9092,CONTROLLER://:29093"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:29092,HOST://localhost:19092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,HOST:PLAINTEXT,CONTROLLER:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:29093"
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "1"
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "1"
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: "0"
    healthcheck:
      test: ["CMD", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:29092", "--list"]
      interval: 5s
      timeout: 5s
      retries: 15
```

```bash
docker compose up -d --wait
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic orders.lifecycle.v1 \
  --partitions 3 --replication-factor 1 \
  --config cleanup.policy=delete --config retention.ms=86400000

printf '%s\n' 'order-100:created' 'order-100:paid' |
  docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server kafka:29092 --topic orders.lifecycle.v1 \
    --reader-property parse.key=true --reader-property key.separator=:

docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic orders.lifecycle.v1 \
  --from-beginning --max-messages 2 --timeout-ms 10000 \
  --formatter-property print.key=true --formatter-property print.partition=true --formatter-property print.offset=true

docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --describe --topic orders.lifecycle.v1
```

두 레코드의 파티션이 같고 오프셋이 증가하는지 확인한다. 토픽 조회 결과에는 파티션별 리더와 복제본, ISR이 표시된다. 컨테이너 안에서 사용하는 주소는 `kafka:29092`, 호스트에서 사용하는 `bootstrap.servers`는 `localhost:19092`다.

Kafka 4.3.2에서 두 레코드가 파티션 1의 오프셋 0과 1로 읽혔다. 토픽의 세 파티션은 모두 브로커 1을 리더와 ISR로 표시했다. 호스트에서 조회한 메타데이터에는 브로커 주소가 `localhost:19092`로 표시됐다.

관련 문서 [Kafka 설계의 배경과 비용](../engineering-design-training/10_understanding_kafkas_design_decisions_through_its_original_paper.md) · [Reliable Asynchronous Messaging Between Services](../microservice-architecture/08_reliable_asynchronous_messaging_between_services.md)
