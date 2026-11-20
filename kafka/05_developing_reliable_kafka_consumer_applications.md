# Developing Reliable Kafka Consumer Applications

Kafka 컨슈머는 파티션에서 레코드를 읽고, 처리를 끝낸 위치를 컨슈머 그룹의 오프셋으로 저장한다. 파티션의 소유권과 커밋 시점을 함께 설계해야 재시작이나 리밸런싱 후에도 작업을 이어갈 수 있다. 예제는 Kafka 4.3.2 Java 클라이언트를 사용한다.

## 1. 컨슈머 그룹과 파티션 할당

`subscribe()`로 토픽을 구독하면 컨슈머가 `group.id`로 지정된 그룹에 참여하고, `poll()`이 할당받은 파티션의 레코드를 반환한다. 한 그룹에서 한 파티션은 한 시점에 최대 한 컨슈머에 할당된다. 파티션 두 개를 세 컨슈머가 같은 그룹에서 구독하면 한 컨슈머는 대기한다. 서로 다른 그룹은 같은 토픽을 각자의 오프셋으로 읽는다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

그룹에 컨슈머가 들어오거나 나갈 때, 구독이 바뀌거나 파티션이 늘어날 때 그룹 코디네이터가 재할당을 조정한다. 이 과정을 리밸런싱이라고 한다. 그룹 프로토콜에 따라 파티션을 나누는 주체와 설정이 달라진다.

| 그룹 프로토콜 | 할당 방식 |
| --- | --- |
| `classic` | 클라이언트의 `partition.assignment.strategy`를 사용한다. `RangeAssignor`는 토픽별로 파티션을 나누고, `RoundRobinAssignor`는 순환 배정한다. `StickyAssignor`는 기존 배정을 최대한 유지하며, `CooperativeStickyAssignor`는 옮겨야 하는 파티션만 단계적으로 회수한다. |
| `consumer` | 브로커가 `group.consumer.assignors`로 제공하는 전략을 사용한다. 클라이언트는 `group.remote.assignor`로 제공된 전략을 선택할 수 있다. 하트비트와 세션 타임아웃도 브로커에서 관리한다. |

특정 파티션만 읽는 조사 도구나 재처리 작업은 `assign(List.of(new TopicPartition("orders.consumer.v1", 0)))`으로 직접 할당할 수 있다. 이 방식은 그룹의 자동 재할당에 참여하지 않으므로 여러 프로세스가 같은 파티션을 읽지 않도록 애플리케이션에서 관리한다. 오프셋을 공유하는 운영 그룹과 분리하여 별도의 `group.id`를 사용하면 재처리가 운영 그룹의 커밋에 영향을 주지 않는다. `seek()`는 현재 읽기 위치를 옮긴다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [Apache Kafka · Consumer Rebalance Protocol](https://kafka.apache.org/43/operations/consumer-rebalance-protocol/)

## 2. 오프셋과 커밋

같은 파티션에도 두 가지 위치가 있다. `position()`은 컨슈머가 다음에 읽을 오프셋이고, 커밋된 오프셋은 같은 그룹이 재시작하거나 파티션을 넘겨받을 때 이어서 읽을 위치다. 오프셋 41까지 처리를 마쳤다면 다음 위치인 42를 커밋한다. 예제의 `records.nextOffsets()`는 이번 `poll()`에서 반환한 배치를 모두 처리했을 때 사용할 파티션별 다음 위치를 제공한다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [Apache Kafka · ConsumerRecords](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRecords.html)

| 설정 | 사용 기준 |
| --- | --- |
| `bootstrap.servers`, `key.deserializer`, `value.deserializer` | 초기 브로커 주소와 키·값을 역직렬화하는 클래스를 지정한다. |
| `group.id`, `group.protocol` | 파티션과 커밋된 오프셋을 공유할 그룹과 그룹 프로토콜을 지정한다. |
| `enable.auto.commit` | 처리 결과를 기준으로 저장 시점을 제어하려면 `false`로 설정한다. |
| `auto.offset.reset` | 유효한 커밋이 없을 때만 적용된다. `earliest`는 보관 중인 가장 이른 위치, `latest`는 현재 로그 끝, `none`은 오류, `by_duration:PT1H`는 현재 시각 기준 1시간 전의 위치를 찾는다. |
| `max.poll.records`, `max.poll.interval.ms` | 한 번에 애플리케이션으로 넘길 레코드 수와 `poll()` 호출 사이의 최대 간격을 정한다. 최악의 배치 처리 시간이 이 간격을 넘는지 확인한다. |
| `fetch.min.bytes`, `fetch.max.wait.ms` | 브로커가 가져오기 요청에 응답할 데이터의 최소 크기와 대기 한도를 조절한다. |

재시작할 때 유효한 커밋이 있으면 `auto.offset.reset=earliest`를 설정해도 그 커밋에서 이어서 읽는다. `commitSync()`는 결과를 기다리므로 처리 완료 후 저장 흐름을 확인하기 쉽다. `commitAsync()`를 쓰면 콜백에서 실패를 관측하고, 뒤늦게 도착한 실패 콜백에서 오래된 오프셋을 그대로 재시도하지 않도록 설계한다. 리밸런싱으로 소유권을 잃어 커밋이 실패하면 갱신된 할당을 확인한다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

DB 반영을 끝낸 뒤 Kafka에 커밋하면 두 작업 사이의 장애로 같은 이벤트를 다시 받을 수 있다. 예를 들어 주문 이벤트 ID에 유일성 제약을 걸고, 중복 확인과 업무 변경을 하나의 DB 트랜잭션으로 묶으면 재처리로 같은 주문이 두 번 반영되는 일을 막을 수 있다. 반대로 처리가 끝나기 전에 커밋하면 장애 복구 시 아직 처리하지 않은 레코드를 건너뛸 수 있다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

## 3. 리밸런싱과 안전한 종료

| 콜백 | 할 일 |
| --- | --- |
| `onPartitionsRevoked()` | 반납할 파티션의 새 작업을 중단한다. 남은 작업을 관리하는 구현에서는 반납 전에 연속으로 처리를 마친 지점까지만 커밋한다. |
| `onPartitionsAssigned()` | 새로 할당된 파티션의 로컬 상태를 초기화하거나 필요한 체크포인트를 복구한다. |
| `onPartitionsLost()` | 다른 컨슈머가 이미 파티션을 이어받았을 수 있으므로 로컬 작업과 상태를 정리한다. 이 콜백에서 잃어버린 파티션의 오프셋을 커밋하지 않는다. |

`KafkaConsumer` 인스턴스는 하나의 스레드가 소유한다. 종료 훅은 스레드 간 호출이 허용된 `wakeup()`으로 소비 스레드를 깨우고, 소비 스레드가 `close()`를 끝낼 때까지 제한 시간 안에서 기다린다. 종료 요청이 마지막 커밋을 중단시키면 다음 실행에서 해당 배치를 다시 받을 수 있다. [Apache Kafka · ConsumerRebalanceListener](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRebalanceListener.html) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

## 4. Docker에서 수동 커밋과 재시작 확인하기

[01번의 Docker Kafka](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)를 띄운 디렉터리에서 두 파티션을 가진 토픽을 만든다. 같은 키로 레코드 두 건을 보내면 두 건의 커밋과 재시작 경계를 한 파티션에서 확인할 수 있다.

```bash
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic orders.consumer.v1 \
  --partitions 2 --replication-factor 1

publish_orders() {
  printf '%s\n' "$@" |
    docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
      --bootstrap-server kafka:29092 --topic orders.consumer.v1 \
      --reader-property parse.key=true --reader-property key.separator=:
}

publish_orders 'order-901:created' 'order-901:paid'
```

다음을 `OrderConsumer.java`로 저장한다. 콘솔 출력은 실습에서 업무 처리를 대신한다. 레코드를 모두 처리한 뒤 다음 오프셋을 동기 커밋하므로 리밸런싱 콜백은 할당 상태만 기록한다.

```java
import java.time.Duration;
import java.util.Collection;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.kafka.clients.consumer.CloseOptions;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRebalanceListener;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;

public class OrderConsumer {
    public static void main(String[] args) {
        var config = new Properties();
        config.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        config.put(ConsumerConfig.GROUP_ID_CONFIG, "orders-consumer-demo");
        config.put(ConsumerConfig.GROUP_PROTOCOL_CONFIG, "classic");
        config.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        config.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        config.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        config.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        config.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, "100");

        var consumer = new KafkaConsumer<String, String>(config);
        var stopping = new AtomicBoolean();
        var stopped = new CountDownLatch(1);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            if (stopped.getCount() == 0) {
                return;
            }
            stopping.set(true);
            consumer.wakeup();
            try {
                stopped.await(15, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "consumer-shutdown"));

        try {
            consumer.subscribe(List.of("orders.consumer.v1"), new ConsumerRebalanceListener() {
                @Override
                public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                    System.out.println("revoked=" + partitions);
                }

                @Override
                public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                    System.out.println("assigned=" + partitions);
                }

                @Override
                public void onPartitionsLost(Collection<TopicPartition> partitions) {
                    System.out.println("lost=" + partitions);
                }
            });

            while (!stopping.get()) {
                var records = consumer.poll(Duration.ofMillis(500));
                for (var record : records) {
                    System.out.printf("processed partition=%d offset=%d key=%s value=%s%n",
                            record.partition(), record.offset(), record.key(), record.value());
                }
                if (!records.isEmpty()) {
                    consumer.commitSync(records.nextOffsets());
                    System.out.println("committed=" + records.nextOffsets());
                }
            }
        } catch (WakeupException e) {
            if (!stopping.get()) {
                throw e;
            }
        } finally {
            try {
                consumer.close(CloseOptions.timeout(Duration.ofSeconds(5)));
                System.out.println("consumer-closed");
            } finally {
                stopped.countDown();
            }
        }
    }
}
```

JDK 17 이상을 사용한다. 아래 명령은 실행 중인 Kafka 컨테이너에서 예제에 필요한 라이브러리를 복사한 뒤 같은 버전의 클라이언트로 컴파일한다.

```bash
mkdir -p lib
docker compose exec -T kafka cat /opt/kafka/libs/kafka-clients-4.3.2.jar > lib/kafka-clients.jar
docker compose exec -T kafka sh -c 'cat /opt/kafka/libs/slf4j-api-*.jar' > lib/slf4j-api.jar
javac -cp 'lib/*' OrderConsumer.java
java -cp '.:lib/*' OrderConsumer
```

`created`와 `paid`의 처리 및 `committed=…` 출력을 확인하고 Ctrl+C로 종료한다. 같은 셸에서 `publish_orders 'order-901:shipped'`를 실행한 뒤 컨슈머를 다시 시작한다. 새 실행에서는 `shipped`부터 읽는다. 다른 터미널에서 아래 명령을 실행해 레코드가 들어간 파티션의 `CURRENT-OFFSET`이 `LOG-END-OFFSET`과 같고 `LAG`가 `0`인지 확인한다. 토픽과 그룹의 정보를 더 자세히 조회하려면 [03번의 소비자 그룹과 오프셋 조회](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#4-소비자-그룹과-오프셋-조회)를 참고한다.

```bash
docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:29092 --describe --group orders-consumer-demo
```

Kafka 4.3.2에서 첫 실행은 오프셋 0과 1을 처리하고 2를 커밋했다. 프로세스를 종료한 뒤 같은 그룹으로 재시작하자 오프셋 2의 `shipped`만 읽었다. 그룹 조회 결과 해당 파티션의 커밋 오프셋은 3, Lag은 0이었다.

## 5. 멀티스레드 컨슈머 설계

파티션 수만큼 독립적으로 소비할 수 있다면 스레드마다 컨슈머를 하나씩 두고 같은 그룹에 참여시키는 구성이 단순하다. 레코드 처리 시간이 길거나 편차가 크면 `poll()`을 호출하는 스레드가 작업을 워커 풀에 맡길 수 있다. 이때 `pause()`와 `resume()`, 오프셋 커밋은 소비 스레드에서 수행하고, 워커의 작업 대기열 크기를 제한한다. 일시 정지한 동안에도 `poll()`을 호출해야 그룹 참여를 유지할 수 있다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

워커가 오프셋 10과 12를 완료했지만 11이 남아 있다면, 11을 넘겨 커밋하면 안 된다. 11이 완료되기 전까지 다음 위치인 11만 저장할 수 있다. 업무 처리 순서도 중요하면 같은 파티션의 작업은 순서대로 실행한다. 파티션을 반납한 뒤에는 이전 할당에서 시작한 워커의 결과가 새 할당의 커밋에 섞이지 않도록 구분한다.

## 6. 컨슈머 Lag과 Burrow

`kafka-consumer-groups.sh --describe`의 그룹 Lag은 파티션마다 `LOG-END-OFFSET - CURRENT-OFFSET`으로 표시된다. 이때 `CURRENT-OFFSET`은 그룹이 커밋한 위치다. 컨슈머 JMX의 `records-lag-max`는 컨슈머 내부의 읽기 위치를 기준으로 계산한다. 워커가 밀려 처리 완료가 늦어질 때는 클라이언트 지표가 낮아도 그룹 Lag이 높을 수 있다. [Apache Kafka · Basic Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/) · [Apache Kafka · Monitoring](https://kafka.apache.org/43/operations/monitoring/)

Lag이 늘면 파티션별 커밋 오프셋과 로그 끝의 변화량을 함께 확인한다. 커밋이 움직이면서 차이가 커지면 유입량과 처리량을 비교한다. 커밋이 멈춰 있으면 처리 오류, 반복되는 리밸런싱, 워커 정체와 커밋 실패를 살핀다. 특정 파티션만 계속 밀리면 키 분포나 해당 파티션의 처리 시간을 확인한다.

Burrow는 여러 시점의 커밋 오프셋과 Lag 변화를 이동 구간에서 평가하고 컨슈머 그룹 상태를 HTTP로 제공하는 별도 모니터링 서비스다. CLI로는 조회 시점의 파티션별 값을 보고, Burrow로는 커밋의 진행 여부와 Lag 추세를 함께 해석할 수 있다. [LinkedIn · Burrow](https://github.com/linkedin/Burrow)
