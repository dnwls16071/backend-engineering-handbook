# Kafka Producer Idempotence and Transactions

전송 응답이 유실되면 Kafka 프로듀서는 같은 배치를 다시 보낼 수 있다. 멱등성은 이 재시도로 생기는 중복 기록을 막는다. 트랜잭션은 여러 출력 레코드와 입력 컨슈머 그룹 오프셋을 하나의 결과로 확정할 때 사용한다. [Apache Kafka · Message Delivery Semantics](https://kafka.apache.org/43/design/design/#message-delivery-semantics)

## 1. 멱등 프로듀서의 보장 범위

브로커가 배치를 기록한 직후 응답이 유실되면, 프로듀서는 기록 성공 여부를 모른 채 재시도한다. 멱등 전송에서 브로커는 프로듀서 ID와 epoch, 파티션별 시퀀스 정보를 이용해 이미 처리한 배치의 재전송을 구분한다. 같은 프로듀서 세션 안에서 클라이언트가 재시도한 배치가 중복으로 기록되는 것을 막고, 허용된 설정 범위에서 파티션별 순서를 유지한다. [Apache Kafka · Message Delivery Semantics](https://kafka.apache.org/43/design/design/#message-delivery-semantics) · [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#enable.idempotence)

| 설정 | 멱등 전송 조건 |
| --- | --- |
| `enable.idempotence` | `true`. Kafka 4.3에서는 충돌하는 설정이 없으면 기본으로 활성화된다. |
| `acks` | `all` |
| `retries` | `0`보다 커야 한다. |
| `max.in.flight.requests.per.connection` | `5` 이하여야 한다. |

`enable.idempotence=true`를 명시하면 충돌하는 설정이 있을 때 `ConfigException`이 발생한다. 같은 키와 값으로 애플리케이션이 `send()`를 두 번 호출하면 두 전송은 별개의 레코드다. 애플리케이션에서 같은 업무 이벤트를 재발행할 수 있다면 업무 이벤트 ID를 재사용하고 수신 쪽에서 중복 반영을 제어한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [Apache Kafka · KafkaProducer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 2. 출력과 입력 오프셋을 한 트랜잭션에 묶기

입력 레코드를 읽어 여러 Kafka 토픽이나 파티션에 결과를 쓰는 작업이라면, 출력과 입력 오프셋을 함께 커밋할 수 있다. 이 흐름에서는 입력 컨슈머의 `enable.auto.commit=false`를 설정하고, `commitSync()`나 `commitAsync()`로 오프셋을 별도 저장하지 않는다. 이후 같은 그룹이 재시작하면 마지막으로 성공한 트랜잭션에서 저장한 위치부터 이어 읽는다. [Apache Kafka · Using Transactions](https://kafka.apache.org/43/design/design/#using-transactions)

1. 프로듀서에 `transactional.id`를 설정하고 `initTransactions()`를 호출한다. ID는 재시작 시 같은 작업이 재사용하고, 동시에 동작하는 프로듀서마다 고유하게 지정한다. 더 새 프로듀서가 같은 ID를 초기화하면 이전 인스턴스는 해당 ID로 계속 쓸 수 없다.
2. 컨슈머가 `poll()`로 입력을 읽고, 프로듀서가 `beginTransaction()` 이후 결과를 `send()`로 전송한다.
3. `sendOffsetsToTransaction(records.nextOffsets(), consumer.groupMetadata())`으로 처리한 파티션의 다음 오프셋을 현재 트랜잭션에 포함한다.
4. `commitTransaction()`이 성공하면 출력이 커밋되고 그룹 오프셋도 확정된다. 트랜잭션을 중단하면 그 출력은 `read_committed`에서 보이지 않으며 그룹 오프셋은 이전 커밋에 머문다. [Apache Kafka · KafkaProducer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

중단 직후에도 `poll()`로 전진한 현재 읽기 위치는 자동으로 되감기지 않는다. 처리를 계속할 때는 현재 할당을 기준으로 마지막 커밋을 다시 읽어 위치를 복원하거나, 프로듀서와 컨슈머를 다시 만들어 그룹에 참여한다. `ProducerFencedException`이 발생한 프로듀서는 닫는다. 커밋 요청이 타임아웃되면 브로커가 이미 커밋했을 수 있으므로, 같은 커밋을 재시도하거나 실행을 종료해 다음 시작 시 복구한다. [Apache Kafka · Using Transactions](https://kafka.apache.org/43/design/design/#using-transactions) · [Apache Kafka · KafkaProducer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 3. 트랜잭션 레코드의 가시성과 처리 범위

| 컨슈머 설정 | 반환하는 레코드 |
| --- | --- |
| `isolation.level=read_uncommitted` | 비트랜잭션 레코드와 아직 진행 중이거나 중단된 트랜잭션 레코드도 읽을 수 있다. |
| `isolation.level=read_committed` | 비트랜잭션 레코드와 커밋된 트랜잭션 레코드를 읽고 중단된 트랜잭션 레코드는 건너뛴다. |

`read_committed`는 파티션의 가장 앞선 미완료 트랜잭션에서 읽기가 멈춘다. 따라서 그 뒤에 기록된 레코드도 해당 트랜잭션이 확정될 때까지 기다릴 수 있다. 이 경계를 LSO(Last Stable Offset)라고 한다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/#isolation.level) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

Kafka에서 입력을 읽고 Kafka에 결과를 쓰는 경우, 정확히 한 번의 처리 결과는 커밋된 출력과 입력 오프셋에 적용된다. 트랜잭션이 중단되면 같은 입력으로 변환 코드가 다시 실행될 수 있다. DB 업데이트, 메일 발송, 외부 API 호출은 Kafka 트랜잭션 경계 밖에 있으므로 해당 시스템에 맞는 멱등 처리나 별도의 일관성 설계가 필요하다. [Apache Kafka · Message Delivery Semantics](https://kafka.apache.org/43/design/design/#message-delivery-semantics)

## 4. Docker에서 중단과 커밋 비교하기

기존 단일 브로커를 시작한 뒤 실습 디렉터리에서 입력·출력 토픽을 만들고 주문 레코드 한 건을 넣는다. 단일 브로커용 내부 트랜잭션 토픽 설정은 기존 Compose 파일에 포함돼 있다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)

```bash
for topic in orders.tx.input.v1 orders.tx.output.v1; do
  docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:29092 --create --topic "$topic" \
    --partitions 1 --replication-factor 1
done

printf '%s\n' 'order-301:paid' |
  docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server kafka:29092 --topic orders.tx.input.v1 \
    --reader-property parse.key=true --reader-property key.separator=:
```

다음을 같은 디렉터리에 `OrderTransaction.java`로 저장한다. 첫 실행은 출력 전송과 오프셋 등록까지 하고 중단한다. 두 번째 실행은 같은 그룹으로 같은 입력을 읽고 둘을 함께 커밋한다. 각 실행은 한 배치만 처리한다.

```java
import java.time.Duration;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.ExecutionException;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

public class OrderTransaction {
    public static void main(String[] args) throws ExecutionException, InterruptedException {
        if (args.length != 1 || (!args[0].equals("abort") && !args[0].equals("commit"))) {
            throw new IllegalArgumentException("Expected abort or commit");
        }

        var input = new Properties();
        input.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        input.put(ConsumerConfig.GROUP_ID_CONFIG, "order-tx-demo");
        input.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        input.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        input.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        input.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        input.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
        input.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, "1");

        var output = new Properties();
        output.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        output.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-tx-demo-worker");
        output.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        output.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        try (var producer = new KafkaProducer<String, String>(output);
             var consumer = new KafkaConsumer<String, String>(input)) {
            producer.initTransactions();
            consumer.subscribe(List.of("orders.tx.input.v1"));
            var records = pollOneBatch(consumer);
            producer.beginTransaction();
            for (var record : records) {
                System.out.printf("input offset=%d value=%s%n", record.offset(), record.value());
                producer.send(new ProducerRecord<>("orders.tx.output.v1", record.key(),
                        args[0] + "-" + record.value())).get();
            }
            producer.sendOffsetsToTransaction(records.nextOffsets(), consumer.groupMetadata());
            if (args[0].equals("abort")) {
                producer.abortTransaction();
            } else {
                producer.commitTransaction();
            }
            System.out.println("transaction=" + args[0]);
        }
    }

    private static ConsumerRecords<String, String> pollOneBatch(KafkaConsumer<String, String> consumer) {
        long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
        do {
            var records = consumer.poll(Duration.ofMillis(500));
            if (!records.isEmpty()) {
                return records;
            }
        } while (System.nanoTime() < deadline);
        throw new IllegalStateException("No input record received");
    }
}
```

JDK 17 이상과 Kafka 4.3.2 Java 클라이언트로 실행한다. `abort`와 `commit` 실행이 모두 입력 오프셋 `0`을 읽는지 확인한다.

```bash
mkdir -p lib
docker compose exec -T kafka cat /opt/kafka/libs/kafka-clients-4.3.2.jar > lib/kafka-clients.jar
docker compose exec -T kafka sh -c 'cat /opt/kafka/libs/slf4j-api-*.jar' > lib/slf4j-api.jar
javac -cp 'lib/*' OrderTransaction.java
java -cp '.:lib/*' OrderTransaction abort
java -cp '.:lib/*' OrderTransaction commit
```

같은 출력 파티션을 처음부터 두 방식으로 읽고, 그룹 조회에서 입력의 커밋 오프셋을 확인한다.

```bash
read_output() {
  docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:29092 --topic orders.tx.output.v1 \
    --partition 0 --from-beginning --timeout-ms 10000 \
    --command-property "isolation.level=$1" --max-messages "$2"
}

read_output read_uncommitted 2
read_output read_committed 1

docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:29092 --describe --group order-tx-demo
```

Kafka 4.3.2에서 두 실행 모두 입력 오프셋 0을 읽었다. 출력은 `read_uncommitted`에서 `abort-paid`와 `commit-paid`가, `read_committed`에서는 `commit-paid`만 조회됐다. 커밋 후 그룹의 `CURRENT-OFFSET`은 1, Lag은 0이었다.
