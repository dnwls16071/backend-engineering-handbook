# Exploring Kafka Partitioning and Consumer Groups with the CLI

토픽을 여러 파티션으로 나누면 프로듀서는 레코드를 분산해 쓰고, 같은 컨슈머 그룹의 구성원은 파티션을 나눠 읽는다. CLI에서 레코드의 키·파티션·오프셋과 그룹의 처리 위치를 함께 보면 두 흐름을 연결할 수 있다. [Kafka 토픽과 파티션](01_apache_kafka_cluster_and_log_fundamentals.md) · [Kafka CLI 기본 명령](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md)

## 1. 토픽을 만들고 전송 결과를 조회한다

01번의 Docker Kafka 4.3.2를 시작한 디렉터리에서 실행한다. 실습마다 새 이름을 써서 기존 소비 위치와 구분한다. 콘솔 프로듀서는 한 줄을 한 레코드로 읽고, `parse.key=true`를 지정하면 구분자 왼쪽을 키로 사용한다. Java 프로듀서에서 객체를 전송할 때는 키와 값 각각에 타입에 맞는 Serializer가 필요하다. 오프셋은 파티션 안의 위치이며, 토픽 전체의 순서를 나타내지 않는다. [Apache Kafka · Quick Start](https://kafka.apache.org/43/getting-started/quickstart/) · [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/)

```bash
kafka_cli() {
  local tool="$1"
  shift
  docker compose exec -T kafka "/opt/kafka/bin/$tool" \
    --bootstrap-server kafka:29092 "$@"
}

topic="orders-cli-$(date +%s)-$$"
group="$topic-reader"

kafka_cli kafka-topics.sh --create --topic "$topic" --partitions 3 --replication-factor 1
kafka_cli kafka-topics.sh --describe --topic "$topic"

printf '%s\n' 'order-1:created' 'order-2:created' 'order-1:paid' |
  kafka_cli kafka-console-producer.sh --topic "$topic" \
    --reader-property parse.key=true --reader-property key.separator=:

kafka_cli kafka-console-consumer.sh --topic "$topic" --group "$group" \
  --from-beginning --max-messages 3 --timeout-ms 10000 \
  --formatter-property print.key=true \
  --formatter-property print.partition=true --formatter-property print.offset=true
```

`order-1`의 두 레코드가 같은 파티션에 있고 오프셋이 증가하는지 확인한다. 다른 키가 같은 파티션에 들어갈 수도 있다. `partitioner.class`를 지정하지 않은 기본 동작에서 키가 없으면 프로듀서는 선택한 파티션을 일정량의 데이터를 배치하는 동안 유지하고, Kafka 버전과 설정에 따라 브로커 상태도 분배에 반영한다. `RoundRobinPartitioner`를 명시하면 키 유무와 무관하게 순환 배정을 사용한다. 공식 문서의 배치 생성 시 분배 불균형 제약도 함께 고려한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#partitioner.class)

## 2. 그룹의 처리 위치와 멤버를 구분한다

`--offsets`는 그룹에서 커밋한 위치와 로그 끝의 차이를 보여 준다. `--members --verbose`는 현재 멤버와 그 멤버가 가진 파티션을 보여 준다. 같은 그룹에 컨슈머를 추가하면 할당이 바뀔 수 있다. 실습의 콘솔 컨슈머를 여러 터미널에서 띄운 경우에는 멤버가 실행 중일 때 할당을 조회한다. 그룹을 지울 때는 해당 실습 그룹의 소비자를 먼저 모두 종료한다. 그룹 삭제는 해당 그룹의 메타데이터와 커밋한 오프셋을 제거한다. [Apache Kafka · Group Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/)

```bash
kafka_cli kafka-consumer-groups.sh --describe --group "$group" --offsets
kafka_cli kafka-consumer-groups.sh --describe --group "$group" --members --verbose
kafka_cli kafka-consumer-groups.sh --describe --group "$group" --state

# 멤버가 모두 종료된 뒤 실습 그룹만 제거한다.
kafka_cli kafka-consumer-groups.sh --delete --group "$group"
```

## 3. 토픽의 설정과 디스크 위치를 확인한다

브로커 옵션은 클러스터의 기본 동작을 정한다. 토픽별 재정의가 있는 옵션은 해당 토픽에서 별도로 바꿀 수 있다. 예를 들어 브로커의 `log.retention.ms`는 기본 보관 시간이고 토픽의 `retention.ms`는 그 토픽의 보관 시간이다. 실습에서는 새 토픽의 보관 시간을 48시간으로 지정해 어떤 값이 재정의됐는지 확인한다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/)

```bash
kafka_cli kafka-configs.sh --describe --entity-type topics --entity-name "$topic"
kafka_cli kafka-configs.sh --alter --entity-type topics --entity-name "$topic" \
  --add-config retention.ms=172800000
kafka_cli kafka-configs.sh --describe --entity-type topics --entity-name "$topic"
kafka_cli kafka-log-dirs.sh --describe --topic-list "$topic"
```

`kafka-log-dirs.sh`가 출력한 경로에서 `<토픽>-<파티션>/<기준 오프셋>.log`를 찾는다. `kafka-dump-log.sh --files <세그먼트 경로> --print-data-log`는 브로커에 접속하는 대신 해당 파일을 읽는다. 메시지 내용을 확인할 때는 실습 세그먼트를 지정한다. 인덱스·롤링·정리 정책의 실습은 28번에서 이어진다. [Apache Kafka · DumpLogSegments](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/DumpLogSegments.java) · [Kafka 로그 세그먼트 검사](28_inspecting_kafka_log_segments_and_cleanup_policies.md)

Kafka 4.3.2 컨테이너에서 `order-1`의 두 레코드는 같은 파티션의 오프셋 0과 1로 읽혔다. 실습 그룹의 Lag은 0이었고, 그룹이 `Empty`인 상태에서 삭제됐다. 토픽의 보관 시간과 로그 디렉터리도 CLI로 조회했다.
