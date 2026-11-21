# Operating a Multi-Broker Kafka Cluster

Kafka 4.3.2의 3노드 KRaft 클러스터에서 컨트롤러 쿼럼과 파티션 복제를 각각 관찰한다. 브로커 한 대를 중지하고 리더가 바뀐 뒤에도 생산과 소비가 이어지는지 확인한다. [01번 클러스터 기초](01_apache_kafka_cluster_and_log_fundamentals.md) · [Apache Kafka · KRaft](https://kafka.apache.org/43/operations/kraft/)

## 1. 컨트롤러와 파티션 리더

| 역할 | 확인할 상태 |
| --- | --- |
| KRaft 컨트롤러 | 투표자들이 메타데이터를 복제한다. 활성 컨트롤러는 브로커 등록, 파티션 배치, 파티션 리더 선출을 조정한다. 투표자 3개 중 2개가 메타데이터 쿼럼의 과반수다. |
| 파티션 리더 | 파티션마다 한 복제본이 리더로 생산 요청을 처리한다. 다른 브로커의 팔로워 복제본은 리더에서 데이터를 가져온다. |

실습에서는 각 프로세스가 `broker,controller` 두 역할을 맡는다. 운영 환경에서는 브로커와 컨트롤러를 따로 배치해 브로커 재시작과 트래픽이 컨트롤러 쿼럼에 주는 영향을 줄인다. [Apache Kafka · KRaft](https://kafka.apache.org/43/operations/kraft/) · [Apache Kafka · Replication](https://kafka.apache.org/43/design/design/#replication)

Kafka 3.x의 ZooKeeper 모드를 점검하던 강의에서는 `zookeeper-shell.sh <호스트>:2181`에 접속해 `ls /brokers/ids`로 등록된 브로커를, `get /controller`로 활성 컨트롤러를, `get /brokers/topics/<토픽>/partitions/<번호>/state`로 파티션의 리더와 ISR을 확인했다. Kafka 4.0부터는 KRaft만 지원한다. 4.3.2에서는 `kafka-metadata-quorum.sh`로 컨트롤러를, `kafka-topics.sh --describe`로 파티션 상태를 확인한다. [Apache Kafka 3.9.2 · ZooKeeper 경로](https://github.com/apache/kafka/blob/3.9.2/core/src/main/scala/kafka/zk/ZkData.scala) · [Apache Kafka · 4.0 업그레이드](https://kafka.apache.org/40/getting-started/upgrade/)

## 2. 3노드 실습 환경 시작하기

빈 디렉터리에 아래 내용을 `compose.yaml`로 저장한다. 각 노드는 고유한 `node.id`를 사용하고, 동일한 클러스터 ID와 정적 투표자 목록을 공유한다. 컨테이너 내부에서 브로커 주소는 `kafka-1:29092`, `kafka-2:29092`, `kafka-3:29092`다. 호스트의 `bootstrap.servers`에는 `localhost:19192,localhost:19193,localhost:19194`를 사용한다. 초기 접속 후에도 모든 브로커가 광고한 주소에 연결할 수 있어야 한다. [Apache Kafka 4.3.2 · 3노드 Docker 예제](https://github.com/apache/kafka/blob/4.3.2/docker/examples/docker-compose-files/cluster/combined/plaintext/docker-compose.yml) · [Apache Kafka · Listener Configuration](https://kafka.apache.org/43/security/listener-configuration/)

정적 쿼럼은 `controller.quorum.voters`에 투표자 ID와 주소를 지정한다. 신규 운영 구성을 검토할 때는 컨트롤러 멤버십을 변경할 수 있는 동적 쿼럼과 `controller.quorum.bootstrap.servers` 설정도 함께 확인한다. [Apache Kafka · Static versus Dynamic KRaft Quorums](https://kafka.apache.org/43/operations/kraft/#static-versus-dynamic-kraft-quorums)

```yaml
x-kafka: &kafka
  image: apache/kafka:4.3.2
  healthcheck:
    test: ["CMD", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "localhost:29092", "--list"]
    interval: 5s
    timeout: 10s
    retries: 24

x-kafka-env: &kafka-env
  CLUSTER_ID: "${KAFKA_LAB_CLUSTER_ID:?Set KAFKA_LAB_CLUSTER_ID}"
  KAFKA_PROCESS_ROLES: "broker,controller"
  KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka-1:29093,2@kafka-2:29093,3@kafka-3:29093"
  KAFKA_LISTENERS: "INTERNAL://:29092,HOST://:9092,CONTROLLER://:29093"
  KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,HOST:PLAINTEXT,CONTROLLER:PLAINTEXT"
  KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
  KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
  KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
  KAFKA_MIN_INSYNC_REPLICAS: "2"
  KAFKA_DEFAULT_REPLICATION_FACTOR: "3"
  KAFKA_UNCLEAN_LEADER_ELECTION_ENABLE: "false"
  KAFKA_AUTO_LEADER_REBALANCE_ENABLE: "false"
  KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "3"
  KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "3"
  KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "2"

services:
  kafka-1:
    <<: *kafka
    ports: ["127.0.0.1:19192:9092"]
    environment:
      <<: *kafka-env
      KAFKA_NODE_ID: "1"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka-1:29092,HOST://localhost:19192"
  kafka-2:
    <<: *kafka
    ports: ["127.0.0.1:19193:9092"]
    environment:
      <<: *kafka-env
      KAFKA_NODE_ID: "2"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka-2:29092,HOST://localhost:19193"
  kafka-3:
    <<: *kafka
    ports: ["127.0.0.1:19194:9092"]
    environment:
      <<: *kafka-env
      KAFKA_NODE_ID: "3"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka-3:29092,HOST://localhost:19194"
```

처음 시작할 때 클러스터 ID를 만들고 `.env`에 보관한다. 재시작할 때는 같은 ID를 사용한다. 실습 데이터는 각 컨테이너에 저장되므로 다시 사용할 때는 `docker compose stop`으로 중지한다.

```bash
kafka_lab_cluster_id=$(docker run --rm --entrypoint /opt/kafka/bin/kafka-storage.sh \
  apache/kafka:4.3.2 random-uuid)
printf 'KAFKA_LAB_CLUSTER_ID=%s\n' "$kafka_lab_cluster_id" > .env
docker compose up -d --wait

kcli() {
  local tool="$1"
  shift
  docker compose exec -T kafka-1 "/opt/kafka/bin/$tool" \
    --bootstrap-server kafka-1:29092,kafka-2:29092,kafka-3:29092 "$@"
}

kcli kafka-metadata-quorum.sh describe --status
kcli kafka-topics.sh --create --topic orders.replicated.v1 \
  --replica-assignment 3:1:2,1:2:3,2:3:1 \
  --config min.insync.replicas=2 --config unclean.leader.election.enable=false
kcli kafka-topics.sh --describe --topic orders.replicated.v1
```

`--replica-assignment`의 쉼표는 파티션을, 콜론은 해당 파티션의 복제본을 구분한다. 각 목록의 첫 번째 ID가 선호 복제본이다. 파티션 0은 브로커 3이 우선이며 복제 계수는 세 파티션 모두 3이다. 쿼럼 상태의 `LeaderId`와 토픽 상태의 `Leader`를 각각 읽는다. [Apache Kafka · Basic Kafka Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/) · [Apache Kafka 4.3.2 · TopicCommand](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)

## 3. 브로커 중지 전후의 ISR 비교

ISR은 리더와 복제를 따라가는 동기 복제본의 집합이다. `acks=all`은 현재 ISR 전체의 복제를 기다리고, `min.insync.replicas=2`는 쓰기를 받아들일 최소 ISR 수를 정한다. 이 구성에서는 ISR이 2개일 때도 쓰기가 가능하며, ISR이 1개로 줄면 리더가 살아 있어도 `acks=all` 쓰기는 최소 조건을 만족하지 못한다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/#min.insync.replicas) · [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#acks)

파티션이 3개일 때 기본 파티셔닝은 키 `order-2`를 파티션 0에 배치한다. 같은 키로 중지 전후에 한 건씩 보내고 파티션 0에서 직접 읽는다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#partitioner.class)

```bash
produce() {
  kcli kafka-console-producer.sh --topic orders.replicated.v1 --sync \
    --command-property acks=all --reader-property parse.key=true \
    --reader-property key.separator=:
}

printf '%s\n' 'order-2:before-stop' | produce

docker compose stop kafka-3
kcli kafka-metadata-quorum.sh describe --status
kcli kafka-topics.sh --describe --topic orders.replicated.v1

printf '%s\n' 'order-2:after-stop' | produce
kcli kafka-console-consumer.sh --topic orders.replicated.v1 --partition 0 \
  --from-beginning --max-messages 2 --timeout-ms 15000 \
  --formatter-property print.partition=true --formatter-property print.offset=true

docker compose start kafka-3
kcli kafka-topics.sh --describe --topic orders.replicated.v1
```

중지 후 파티션 0의 리더는 브로커 1 또는 2로 옮겨가고, `Replicas`에는 3이 계속 남는다. `Isr`에서 3이 빠졌는지 확인한다. 복구 뒤에는 ISR에 3이 다시 들어올 때까지 조회를 반복한다. 이 구성에서 두 노드를 동시에 중지하면 컨트롤러 과반수도 잃으므로 ISR 부족만 따로 관찰하기 어렵다. [Apache Kafka · KRaft](https://kafka.apache.org/43/operations/kraft/) · [Apache Kafka · Replication](https://kafka.apache.org/43/design/design/#replication)

## 4. 리더 선출과 ELR

- **선호 리더 선출**은 첫 번째로 배치된 복제본이 ISR에 복귀한 뒤 리더를 원래 배치로 되돌린다. 실습은 자동 리밸런싱을 꺼 두었으므로 파티션 0에서 수동 선출 전후를 비교할 수 있다. [Apache Kafka · Balancing Leadership](https://kafka.apache.org/43/operations/basic-kafka-operations/#balancing-leadership)
- **ELR**(Eligible Leader Replicas)은 현재 ISR 밖에도 안전하게 리더가 될 수 있는 복제본을 추적한다. 엄격한 최소 ISR 규칙으로 ISR이 `min.insync.replicas`보다 적을 때 데이터 파티션의 high watermark 전진을 막는다. 컨트롤러는 ISR, 펜싱되지 않은 ELR, 펜싱되지 않은 직전 리더 순서로 안전한 후보를 찾는다. 새 클러스터에서는 Kafka 4.1부터 ELR이 기본 활성화되며, `--describe`에서 `Elr`와 `LastKnownElr`를 볼 수 있다. 브로커 한 대만 중지하는 이 실습에서는 두 필드가 비어 있을 수 있다. [Apache Kafka · Eligible Leader Replicas](https://kafka.apache.org/43/operations/eligible-leader-replicas/) · [Apache Kafka 4.3.2 · TopicCommand](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- **Unclean leader election**은 안전한 후보가 없을 때 뒤처진 복제본을 리더로 승격할 수 있는 복구 선택이다. 그 복제본에 없는 레코드가 유실될 수 있다. 확인된 레코드 보존을 우선한다면 `unclean.leader.election.enable=false`를 유지하고 안전한 복제본이 돌아올 때까지 해당 파티션의 복구를 기다린다. 복제 계수 3, `min.insync.replicas=2`, `acks=all`을 함께 사용하고 장애 범위가 겹치지 않도록 복제본을 배치한다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/#unclean.leader.election.enable) · [Apache Kafka · Replication](https://kafka.apache.org/43/design/design/#replication)

```bash
kcli kafka-leader-election.sh --election-type preferred \
  --topic orders.replicated.v1 --partition 0
kcli kafka-topics.sh --describe --topic orders.replicated.v1
docker compose stop
```

Kafka 4.3.2에서 브로커 3을 중지하자 파티션 0의 리더가 브로커 1로 이동했다. 중지 전후에 발행한 두 레코드를 모두 읽었고, 브로커 3이 ISR에 복귀한 뒤 선호 리더 선출로 파티션 0의 리더가 다시 3이 됐다.
