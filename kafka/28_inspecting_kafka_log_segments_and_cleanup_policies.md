# Inspecting Kafka Log Segments and Cleanup Policies

Kafka 4.3.2의 파티션 로그에서 세그먼트 파일을 읽고, `delete`와 `compact`가 적용된 토픽의 오프셋 변화를 비교한다. 실습은 별도 단일 브로커에서 진행한다. [01번 로그 기초](01_apache_kafka_cluster_and_log_fundamentals.md#3-로그-세그먼트와-보관-정책) · [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/)

## 1. 로그 파일의 구조와 롤링

브로커는 파티션의 활성 세그먼트에 레코드 배치를 추가한다. `segment.bytes`에 도달하거나 `segment.ms`가 지나면 새 세그먼트로 넘길 수 있다. 시간 기준 롤링을 관찰할 때는 대기 후 레코드를 추가해 전환을 유도한다. 파일명 앞의 숫자는 세그먼트의 기준 오프셋이다. [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/)

| 파일 | 담는 정보 |
| --- | --- |
| `.log` | 실제 키·값, 타임스탬프 등을 포함하는 레코드 배치 |
| `.index` | 기준 오프셋에 대한 상대 오프셋과 `.log`의 바이트 위치를 연결하는 희소 인덱스 |
| `.timeindex` | 타임스탬프와 상대 오프셋을 연결하는 희소 인덱스 |

타임스탬프로 조회하면 `.timeindex`에서 후보 오프셋을 찾고, `.index`로 해당 위치 근처를 찾은 뒤 로그를 읽는다. `index.interval.bytes`에 따라 중간 위치를 기록하므로 모든 레코드가 인덱스에 나타나지는 않는다. [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/#index.interval.bytes)

## 2. 롤링된 세그먼트 덤프하기

빈 디렉터리에 [01번 Compose](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)를 `compose.yaml`로 저장한다. 이 복사본에서 `kafka` 서비스의 `ports` 블록과 `HOST` 리스너를 제거한다. `KAFKA_LISTENERS`는 `INTERNAL://:29092,CONTROLLER://:29093`, `KAFKA_ADVERTISED_LISTENERS`는 `INTERNAL://kafka:29092`, `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP`은 `INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT`로 바꾼다. 같은 서비스의 `environment`에 다음 설정을 추가한다. 조회 간격을 줄여 실습에서 정리 결과를 관찰하기 쉽게 한다. [Apache Kafka · Broker Configs](https://kafka.apache.org/43/configuration/broker-configs/)

```yaml
KAFKA_LOG_DIRS: /tmp/kafka-segment-lab
KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS: "5000"
KAFKA_LOG_CLEANER_BACKOFF_MS: "1000"
```

짧은 시간 안에 세그먼트를 돌리기 위해 `segment.ms=2000`을 적용하고, 첫 발행과 두 번째 발행 사이를 3초 이상 벌린다. 파일을 먼저 확인할 수 있도록 시간 보관 제한은 `-1`로 둔다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/) · [Apache Kafka 4.3.2 · ConsoleProducer](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/ConsoleProducer.java)

```bash
docker compose -p kafka-segments up -d --wait

kseg() {
  docker compose -p kafka-segments exec -T kafka "$@"
}

kcli() {
  local tool="$1"
  shift
  kseg "/opt/kafka/bin/$tool" --bootstrap-server kafka:29092 "$@"
}

kcli kafka-topics.sh --create --topic orders.segments.v1 \
  --partitions 1 --replication-factor 1 --config cleanup.policy=delete \
  --config segment.ms=2000 --config index.interval.bytes=1 \
  --config retention.ms=-1 --config file.delete.delay.ms=5000

printf '%s\n' 'event-01' 'event-02' 'event-03' |
  kcli kafka-console-producer.sh --topic orders.segments.v1 --sync
sleep 3
printf '%s\n' 'event-04' 'event-05' 'event-06' |
  kcli kafka-console-producer.sh --topic orders.segments.v1 --sync

kcli kafka-log-dirs.sh --describe --topic-list orders.segments.v1
kseg ls -l /tmp/kafka-segment-lab/orders.segments.v1-0
```

파일 목록에 `00000000000000000000`보다 큰 기준 오프셋이 표시되면 첫 세그먼트가 닫혔음을 확인할 수 있다. 같은 기준 오프셋의 파일 세 개를 임시 디렉터리에 복사하고 `kafka-dump-log.sh`로 읽는다. `--print-data-log`는 레코드 값을 출력하므로 이 예제의 샘플 데이터로 사용한다. [Apache Kafka 4.3.2 · DumpLogSegments](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/DumpLogSegments.java)

```bash
kseg sh -ec '
  source=/tmp/kafka-segment-lab/orders.segments.v1-0
  base=00000000000000000000
  snapshot=$(mktemp -d)
  for ext in log index timeindex; do
    cp "$source/$base.$ext" "$snapshot/"
  done
  /opt/kafka/bin/kafka-dump-log.sh --print-data-log \
    --files "$snapshot/$base.log,$snapshot/$base.index,$snapshot/$base.timeindex"
'
```

`.log`의 배치 오프셋과 `.index`의 바이트 위치를 대조한다. `.timeindex`에는 인덱싱할 타임스탬프와 오프셋이 표시된다. 짧은 간격에 기록한 레코드는 같은 타임스탬프를 가질 수 있어 시간 인덱스 항목 수가 더 적을 수 있다. [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/)

## 3. `delete`와 시작 오프셋

`cleanup.policy=delete`는 `retention.ms` 또는 파티션별 `retention.bytes` 조건에 따라 오래된 세그먼트를 제거한다. 시간 기준은 세그먼트 안의 가장 큰 레코드 타임스탬프를 사용한다. 브로커는 주기적으로 삭제 대상을 확인하고 `file.delete.delay.ms`가 지나면 파일을 제거하므로, 읽을 수 있는 시작 오프셋이 먼저 바뀔 수 있다. [Apache Kafka · Log Implementation](https://kafka.apache.org/43/implementation/log/) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/#retention.ms)

```bash
kcli kafka-get-offsets.sh --topic orders.segments.v1 --time -2
kcli kafka-configs.sh --entity-type topics --entity-name orders.segments.v1 \
  --alter --add-config retention.ms=5000
```

아래 두 조회를 몇 초 간격으로 반복한다. `kafka-get-offsets.sh --time -2`는 가장 이른 오프셋을 보여 준다. 세그먼트가 만료되면 시작 오프셋이 전진하고 해당 파일은 지연 후 사라진다. [03번 CLI 도구](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#5-다른-운영-도구와-버전-호환성)

```bash
kcli kafka-get-offsets.sh --topic orders.segments.v1 --time -2
kseg ls -l /tmp/kafka-segment-lab/orders.segments.v1-0
```

## 4. `compact`와 tombstone

`cleanup.policy=compact`는 같은 파티션 안에서 키별 최신 상태가 남도록 이전 값을 비동기로 정리한다. 키가 있고 값이 `null`인 tombstone은 그 키의 삭제를 나타낸다. 로그 클리너는 이전 값을 제거하고, tombstone도 `delete.retention.ms` 보관 기간을 지난 뒤 후속 정리에서 제거할 수 있다. `cleanup.policy=compact,delete`에서는 컴팩션과 세그먼트 보관 한도를 모두 적용하므로 오래된 키의 최신 레코드도 보관 정책에 따라 사라질 수 있다. [Apache Kafka · Log Compaction](https://kafka.apache.org/43/design/design/#log-compaction) · [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/#delete.retention.ms)

```bash
kcli kafka-topics.sh --create --topic orders.compacted.v1 \
  --partitions 1 --replication-factor 1 --config cleanup.policy=compact \
  --config segment.ms=2000 --config min.cleanable.dirty.ratio=0.01 \
  --config delete.retention.ms=120000

produce_compact() {
  kcli kafka-console-producer.sh --topic orders.compacted.v1 --sync \
    --reader-property parse.key=true --reader-property key.separator=: \
    --reader-property null.marker=__NULL__
}

printf '%s\n' 'order-1:created' 'order-2:paid' 'order-1:shipped' 'order-2:__NULL__' |
  produce_compact
sleep 3
printf '%s\n' 'marker:rolled' | produce_compact
```

두 번째 발행은 활성 세그먼트 전환을 유도한다. 아래 조회를 반복해 `order-1:created`와 `order-2:paid`가 사라지고 `order-1:shipped`의 오프셋 2가 유지되는지 확인한다. tombstone과 이전 값이 보이는 동안에는 클리너가 아직 해당 정리 단계를 마치지 않았을 수 있다. 컴팩션은 레코드를 다른 오프셋으로 옮기지 않으므로 조회 결과에는 번호가 건너뛸 수 있다. [Apache Kafka · Log Compaction](https://kafka.apache.org/43/design/design/#log-compaction) · [Apache Kafka 4.3.2 · ConsoleProducer](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/ConsoleProducer.java)

```bash
kcli kafka-console-consumer.sh --topic orders.compacted.v1 --partition 0 \
  --from-beginning --timeout-ms 4000 --formatter-property print.offset=true \
  --formatter-property print.key=true
```

더 읽을 데이터가 없는 상태에서 시간 제한에 이르면 소비자가 종료된다. 실습이 끝나면 `docker compose -p kafka-segments stop`으로 실습 브로커를 중지한다.

Kafka 4.3.2에서 시간 기준으로 롤링된 세그먼트와 인덱스를 덤프했다. 보관 시간이 지나자 `orders.segments.v1`의 시작 오프셋이 0에서 6으로 이동했다. 컴팩션 뒤에는 `order-1`의 최신 값 `shipped`가 오프셋 2에 남았고, `order-2`는 오프셋 3의 tombstone으로 읽혔다.
