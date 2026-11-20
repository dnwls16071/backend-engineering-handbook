# Publishing File Events to Kafka

피자 주문을 UTF-8 텍스트로 받아 Kafka 레코드로 발행한다. 완성된 파일은 처음부터 한 번 읽고, 계속 추가되는 파일은 EOF 이후에 새 줄을 기다린다. 한 파일에서 읽은 이벤트를 같은 프로듀서로 발행하면 전송 확인과 종료를 한곳에서 관리할 수 있다. [Apache Kafka · KafkaProducer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 1. 파일 한 줄을 Kafka 레코드로 바꾼다

한 줄은 `eventId|orderId|status`다. `eventId`는 재발행 때도 유지할 불변 식별자다. 프로듀서는 `orderId`를 키로 써 같은 파티셔닝 조건에서 한 주문의 상태 변경을 같은 파티션으로 보낸다. Kafka 값에는 원래 한 줄을 넣어 24번의 소비자에서도 `eventId`를 사용할 수 있게 한다. [Kafka Producer의 키와 파티션](04_developing_reliable_kafka_producer_applications.md) · [PostgreSQL로 이벤트 저장하기](24_consuming_kafka_events_into_postgresql.md)

| 읽는 방식 | 파일 처리 |
| --- | --- |
| 일괄 읽기 | 파일 끝에서 종료한다. 마지막 줄에 줄바꿈이 빠져 있으면 오류를 반환한다. |
| 추가 내용 추적 | EOF에서 짧게 대기한다. 쓰는 쪽이 줄바꿈을 추가할 때까지 미완성 줄의 시작 위치를 유지한다. |

실습 파일은 기존 줄을 유지하고 뒤에만 추가한다. 파일 회전과 중간 수정까지 지원할 때는 파일 식별자와 위치를 함께 추적한다. 변경 알림을 사용하더라도 알림 자체는 새 레코드가 아니므로 마지막 위치부터 완성된 줄을 읽어야 한다. [JDK 17 · RandomAccessFile](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/io/RandomAccessFile.html)

## 2. Java에서 파일 읽기와 전송을 연결한다

다음을 `FileOrderProducer.java`로 저장한다. `send().get()`은 한 줄의 전송 결과를 확인한 뒤 다음 줄을 읽게 한다. 읽기와 전송을 병렬화하려면 콜백을 사용하는 동안 미확인 요청 수를 제한하고, 체크포인트는 연속해서 확인된 위치까지만 전진시킨다. 이 예제는 파일 위치를 저장하지 않아 재시작 시 처음부터 읽는다. 재발행을 구분할 수 있도록 원본 `eventId`를 보존한다. [Apache Kafka · KafkaProducer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html) · [Kafka 멱등성과 트랜잭션](06_kafka_producer_idempotence_and_transactions.md)

```java
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.Properties;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

public class FileOrderProducer {
    static final String TOPIC = "pizza.file-events.v1";

    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2 || (args.length == 2 && !args[1].equals("--follow"))) {
            throw new IllegalArgumentException("Usage: FileOrderProducer <file> [--follow]");
        }
        boolean follow = args.length == 2;
        var config = new Properties();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,
                System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"));
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        config.put(ProducerConfig.ACKS_CONFIG, "all");
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");

        try (var input = new RandomAccessFile(args[0], "r");
             var producer = new KafkaProducer<String, String>(config)) {
            while (true) {
                String line = readCompleteLine(input);
                if (line == null) {
                    if (follow) {
                        Thread.sleep(250);
                        continue;
                    }
                    if (input.getFilePointer() < input.length()) {
                        throw new IOException("Input ends with an incomplete line");
                    }
                    return;
                }
                var event = PizzaOrderEvent.parse(line);
                var result = producer.send(new ProducerRecord<>(TOPIC, event.orderId(), line)).get();
                System.out.printf("sent event=%s partition=%d offset=%d%n",
                        event.eventId(), result.partition(), result.offset());
            }
        }
    }

    private static String readCompleteLine(RandomAccessFile input) throws IOException {
        long start = input.getFilePointer();
        String raw = input.readLine();
        if (raw == null) {
            return null;
        }
        // readLine also returns a partial line at EOF. Accept only LF or CRLF.
        input.seek(input.getFilePointer() - 1);
        if (input.read() != '\n') {
            input.seek(start);
            return null;
        }
        return new String(raw.getBytes(StandardCharsets.ISO_8859_1), StandardCharsets.UTF_8);
    }
}

record PizzaOrderEvent(String eventId, String orderId, String status) {
    static PizzaOrderEvent parse(String line) {
        if (line == null) {
            throw new IllegalArgumentException("Expected a pizza order event");
        }
        String[] fields = line.split("[|]", -1);
        if (fields.length != 3 || fields[0].isBlank() || fields[1].isBlank() || fields[2].isBlank()) {
            throw new IllegalArgumentException("Expected eventId|orderId|status");
        }
        return new PizzaOrderEvent(fields[0], fields[1], fields[2]);
    }
}
```

## 3. 이미 있는 줄과 나중에 추가한 줄을 확인한다

01번의 Kafka 컨테이너에서 클라이언트 라이브러리를 받아 JDK 17 이상으로 컴파일한다. 새 토픽과 파일로 실습을 시작한다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)

```bash
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --topic pizza.file-events.v1 \
  --partitions 3 --replication-factor 1

mkdir -p lib
docker compose exec -T kafka cat /opt/kafka/libs/kafka-clients-4.3.2.jar > lib/kafka-clients.jar
docker compose exec -T kafka sh -c 'cat /opt/kafka/libs/slf4j-api-*.jar' > lib/slf4j-api.jar
javac -cp 'lib/*' FileOrderProducer.java

printf '%s\n' 'evt-1|order-901|CREATED' > pizza-orders.txt
java -cp '.:lib/*' FileOrderProducer pizza-orders.txt --follow
```

첫 `sent` 로그를 확인한 뒤 같은 디렉터리의 다른 터미널에서 아래 줄을 추가한다. 두 이벤트가 같은 파티션으로 전송되는지 확인한다. `--follow` 없이 실행하면 기존 줄만 읽고 종료한다. 파일을 다시 읽으면 이미 확인한 레코드도 새 전송이 될 수 있으므로, 24번에서는 DB에서 `eventId`의 중복 반영을 막는다.

```bash
printf '%s\n' 'evt-2|order-901|PAID' >> pizza-orders.txt
docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic pizza.file-events.v1 --from-beginning \
  --max-messages 2 --timeout-ms 10000 --formatter-property print.key=true
```

Kafka 4.3.2에서 기존 줄과 나중에 추가한 줄이 같은 파티션에 순서대로 발행됐다. UTF-8 한글을 포함한 줄은 줄바꿈을 추가한 뒤에만 발행되는 것도 확인했다.
