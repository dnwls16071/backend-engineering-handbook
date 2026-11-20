# Developing Reliable Kafka Producer Applications

Kafka Producer는 레코드를 직렬화하고 파티션을 선택한 뒤, 파티션 리더에 배치로 전송한다. 애플리케이션은 **어디에 기록할지**, **어떤 확인을 기다릴지**, **실패를 어떻게 관측할지**를 정한다. 예제는 Java 17과 Apache Kafka 4.3.2의 `org.apache.kafka:kafka-clients:4.3.2`를 사용한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 1. 키와 파티션을 선택한다

| 입력 또는 설정 | 파티션 선택 |
| --- | --- |
| `ProducerRecord`에 파티션 번호 지정 | 해당 번호로 전송한다. 번호는 토픽의 파티션 범위 안에 있어야 한다. |
| 파티션 생략, 키 지정 | 기본 Java Producer는 직렬화한 키를 해시해 파티션을 고른다. |
| 파티션과 키 생략 | 기본 Producer는 배치를 효율적으로 채우도록 파티션을 선택한다. 설정에 따라 브로커 처리 성능도 선택에 반영할 수 있다. |
| `partitioner.class` 설정 | 파티션 번호를 생략했을 때 사용자 정의 `Partitioner`에 선택을 맡긴다. |

주문별 처리 순서가 중요하다면 주문 ID를 같은 방식으로 직렬화하고, 모든 생산자가 동일한 파티셔닝 규칙을 적용한다. 파티션 수나 커스텀 규칙을 바꾸면 같은 키의 이후 레코드가 다른 파티션으로 갈 수 있다. 고정 파티션이나 일부 키에 집중되는 규칙은 파티션별 유입량으로 확인한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [Partitioner API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/Partitioner.html)

## 2. 전송 옵션과 확인 수준을 정한다

| 옵션 | 제어하는 동작 |
| --- | --- |
| `bootstrap.servers`, `key.serializer`, `value.serializer` | 초기 브로커 주소와 키·값을 바이트로 변환하는 방법 |
| `batch.size`, `linger.ms`, `compression.type` | 파티션별 배치 크기, 배치를 모을 대기 시간, 압축 형식 |
| `buffer.memory`, `max.block.ms` | 대기 레코드에 사용하는 버퍼와 메타데이터·버퍼 확보를 기다리는 한도 |
| `request.timeout.ms`, `delivery.timeout.ms` | 개별 요청 응답 대기와 배치 대기·요청·재시도를 포함한 전송 결과 보고 기한 |
| `enable.idempotence`, `retries`, `max.in.flight.requests.per.connection` | Producer의 재시도 중 중복 기록과 전송 순서에 영향을 주는 설정 |

`delivery.timeout.ms`는 `request.timeout.ms + linger.ms` 이상으로 설정한다. 멱등 전송에는 `acks=all`, 양수 `retries`, 연결당 진행 중 요청 수 5 이하가 필요하다. Producer의 멱등성 범위는 같은 Producer가 내부에서 재시도하는 전송이다. 애플리케이션이 결과 미상의 이벤트를 다시 제출하는 상황에는 동일한 업무 이벤트 ID를 사용해 중복 처리할 때의 결과를 설계한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

| `acks` | 전송 결과를 판단하는 기준 |
| --- | --- |
| `0` | 브로커 응답을 기다리지 않는다. Producer에서 성공으로 반환돼도 브로커의 기록 여부는 확인할 수 없다. |
| `1` | 파티션 리더가 로컬 로그에 기록한 뒤 응답한다. 팔로워가 따라잡기 전에 리더가 장애를 겪으면 기록을 잃을 수 있다. |
| `all` | 리더 및 현재 ISR의 복제를 기다린다. ISR 수가 `min.insync.replicas`를 충족하지 못하면 쓰기가 실패할 수 있다. |

예를 들어 복제 계수 3과 `min.insync.replicas=2`를 적용한 토픽은 현재 ISR이 두 개일 때 `acks=all`의 최소 조건을 충족한다. 같은 토픽의 ISR이 하나로 줄면 가용성보다 최소 복제 조건을 우선한다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/) · [복제와 ISR](01_apache_kafka_cluster_and_log_fundamentals.md#4-복제-isr-생산자-확인)

## 3. Java로 키, 파티션 번호, 커스텀 파티셔너를 검증한다

[01번의 Docker Kafka](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)를 실행한 뒤 파티션 세 개인 `orders.producer.default.v1`과 `orders.producer.custom.v1`을 만든다. [03번의 토픽 생성 명령](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#2-토픽-생성과-설정-변경)에서 토픽 이름과 파티션 수를 바꾸면 된다. 기본 실행은 첫 토픽을, `custom` 인자를 전달한 실행은 두 번째 토픽을 사용한다.

```java
import java.time.Duration;
import java.util.Arrays;
import java.util.Map;
import java.util.Properties;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Partitioner;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.Cluster;
import org.apache.kafka.common.serialization.StringSerializer;

public class OrderProducer {
    public static void main(String[] args) throws Exception {
        boolean custom = args.length > 0 && args[0].equals("custom");
        String topic = custom ? "orders.producer.custom.v1" : "orders.producer.default.v1";

        var config = new Properties();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        config.put(ProducerConfig.ACKS_CONFIG, "all");
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
        config.put(ProducerConfig.LINGER_MS_CONFIG, "5");
        config.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, "10000");
        config.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, "30000");
        if (custom) {
            config.put(ProducerConfig.PARTITIONER_CLASS_CONFIG, OrderPartitioner.class.getName());
        }

        var producer = new KafkaProducer<String, String>(config);
        try {
            var created = producer.send(new ProducerRecord<>(topic, "order-101", "created"));
            var paid = producer.send(new ProducerRecord<>(topic, "order-101", "paid"),
                    (metadata, error) -> {
                        if (error != null) {
                            System.err.printf("paid callback failed: %s%n", error);
                        } else {
                            report("paid-callback", metadata);
                        }
                    });
            var pinned = producer.send(new ProducerRecord<>(topic, 2, "order-202", "created"));
            var priority = producer.send(new ProducerRecord<>(topic, "priority-301", "created"));

            report("created", created.get());
            report("paid", paid.get());
            report("pinned", pinned.get());
            report("priority", priority.get());
        } finally {
            producer.close(Duration.ofSeconds(10));
        }
    }

    private static void report(String label, RecordMetadata metadata) {
        System.out.printf("%s topic=%s partition=%d offset=%d%n",
                label, metadata.topic(), metadata.partition(), metadata.offset());
    }

    public static class OrderPartitioner implements Partitioner {
        @Override
        public int partition(String topic, Object key, byte[] keyBytes, Object value,
                             byte[] valueBytes, Cluster cluster) {
            if (keyBytes == null) {
                throw new IllegalArgumentException("An order key is required");
            }
            int count = cluster.partitionCountForTopic(topic);
            if (count == 1 || (key instanceof String text && text.startsWith("priority-"))) {
                return 0;
            }
            return 1 + Math.floorMod(Arrays.hashCode(keyBytes), count - 1);
        }

        @Override public void configure(Map<String, ?> configs) {}
        @Override public void close() {}
    }
}
```

기본 실행에서 `order-101`의 두 레코드가 같은 파티션에 있고 오프셋이 증가하는지 확인한다. 두 실행 모두 `pinned`는 파티션 2로 전송된다. 커스텀 실행에서 `priority-` 키는 파티션 0에, 일반 키는 나머지 파티션에 간다.

기본 Producer로 키 없이 발행할 때는 `new ProducerRecord<>(topic, "created")`처럼 토픽과 값만 전달한다. 예제의 커스텀 파티셔너는 키가 있는 레코드를 입력 조건으로 삼는다.

Docker의 Kafka 4.3.2에서 `priority-301`은 기본 파티셔너로 파티션 2에, 커스텀 파티셔너로 파티션 0에 기록됐다. 두 실행 모두 같은 주문 키의 레코드가 같은 파티션에 기록됐고, Future·Callback의 메타데이터와 Consumer가 읽은 위치가 일치했다.

## 4. 전송 결과를 확인하고 종료한다

`send(...)`는 비동기로 전송하며, `Future.get()`으로 성공 메타데이터 또는 예외를 확인할 수 있다. Callback을 붙이면 전송이 완료될 때 결과를 받아 기록할 수 있다. Callback은 보통 Producer의 I/O 스레드에서 실행되므로 빠르게 반환하고, 무거운 작업은 별도 실행기로 넘긴다. [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

장기 실행 애플리케이션을 종료할 때는 새 입력 수락을 먼저 멈추고 진행 중인 전송의 결과를 수집한다. `flush()`는 호출 전에 제출한 전송이 성공이나 실패로 완료될 때까지 기다린다. `close(Duration)`는 정해진 시간 안에 전송을 끝내고 자원을 닫는다. 기한을 넘겨 실패한 전송까지 성공으로 집계하지 않도록 Future나 Callback 결과를 확인한다. [KafkaProducer · flush and close](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
