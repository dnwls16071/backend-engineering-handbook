# Serializing Kafka Records with Jackson

Kafka는 레코드의 키와 값을 바이트로 저장한다. `Customer`를 JSON 값으로 발행하려면 프로듀서의 `Serializer<Customer>`와 컨슈머의 `Deserializer<Customer>`가 같은 형식으로 변환해야 한다. 예제는 Kafka 클라이언트 4.3.2와 Jackson Databind 2.21.7을 사용한다. [Kafka · Serializer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/serialization/Serializer.html) · [Kafka · Deserializer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/serialization/Deserializer.html) · [FasterXML · Jackson Databind 2.21.7](https://github.com/FasterXML/jackson-databind/releases/tag/jackson-databind-2.21.7)

## 1. 고객 ID와 JSON 값의 계약을 정한다

키의 타입은 `String`이고 값은 `Customer`다. `StringSerializer`로 UTF-8 고객 ID를 보내고, 값은 `ObjectMapper.writeValueAsBytes()`로 JSON 바이트를 만든다. `ObjectMapper`는 한 번 구성한 뒤 재사용한다. 프로듀서와 컨슈머는 설정에 지정한 변환 클래스를 공개 기본 생성자로 만들고 `configure()`를 호출한다. 변환기가 자원을 직접 소유하면 `close()`에서 해제한다. [FasterXML · Jackson Databind 2.x](https://github.com/FasterXML/jackson-databind/tree/2.21) · [Kafka · Serializer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/serialization/Serializer.html)

| 입력 | 변환 결과 |
| --- | --- |
| `Customer("c-101", "Kim")` | `id`, `name` 필드를 담은 JSON 바이트 |
| Kafka 값이 `null` | 변환 결과도 `null`. `cleanup.policy=compact`를 적용한 토픽에 키와 함께 기록하면 이전 값을 정리할 tombstone이 된다. |
| 빈 바이트, JSON 리터럴 `null`, 깨진 JSON, 필수 필드가 없는 JSON | `SerializationException`을 발생시킨다. |

Kafka의 값 `null`과 JSON 문자열에 기록된 `null`은 서로 다른 입력이다. 역직렬화 오류를 `null`로 반환하면 소비자가 잘못된 데이터를 삭제 이벤트로 처리할 수 있다. 기본 `KafkaConsumer`의 `poll()`에서 `RecordDeserializationException`이 발생하면 파티션과 오프셋으로 실패 레코드를 식별할 수 있다. [Kafka · Log Compaction](https://kafka.apache.org/43/design/design/#log-compaction) · [Kafka · RecordDeserializationException](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/errors/RecordDeserializationException.html)

## 2. JSON Lines 파일을 읽어 고객 레코드를 발행한다

[18번 Gradle 실습](18_building_and_debugging_java_kafka_producers.md#1-gradle-멀티-프로젝트를-구성한다)의 `pizza-producer` 의존성에 `implementation 'com.fasterxml.jackson.core:jackson-databind:2.21.7'`을 추가한다. 아래 코드를 같은 모듈의 `src/main/java/pizza/CustomerFilePublisher.java`에 저장한다.

```java
package pizza;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import java.util.concurrent.ExecutionException;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.errors.SerializationException;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.Serializer;
import org.apache.kafka.common.serialization.StringSerializer;

public class CustomerFilePublisher {
    private static final String TOPIC = "customers.json.v1";
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Customer(String id, String name) {
        public Customer {
            if (id == null || id.isBlank() || name == null || name.isBlank()) {
                throw new IllegalArgumentException("id and name are required");
            }
        }
    }

    public static final class CustomerSerializer implements Serializer<Customer> {
        @Override
        public byte[] serialize(String topic, Customer customer) {
            if (customer == null) {
                return null;
            }
            try {
                return MAPPER.writeValueAsBytes(customer);
            } catch (JsonProcessingException error) {
                throw new SerializationException("Cannot encode customer for " + topic, error);
            }
        }
    }

    public static final class CustomerDeserializer implements Deserializer<Customer> {
        @Override
        public Customer deserialize(String topic, byte[] data) {
            if (data == null) {
                return null;
            }
            try {
                Customer customer = MAPPER.readValue(data, Customer.class);
                if (customer == null) {
                    throw new SerializationException("Expected a customer object for " + topic);
                }
                return customer;
            } catch (IOException error) {
                throw new SerializationException("Cannot decode customer from " + topic, error);
            }
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("Expected path to JSON Lines file");
        }
        var config = new Properties();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, CustomerSerializer.class.getName());
        try (var producer = new KafkaProducer<String, Customer>(config)) {
            publish(producer, Path.of(args[0]));
        }
    }

    static void publish(Producer<String, Customer> producer, Path path)
            throws IOException, InterruptedException, ExecutionException {
        try (var reader = Files.newBufferedReader(path, StandardCharsets.UTF_8);
             var deserializer = new CustomerDeserializer()) {
            int lineNumber = 0;
            for (String line; (line = reader.readLine()) != null; ) {
                lineNumber++;
                if (line.isBlank()) {
                    continue;
                }
                Customer customer;
                try {
                    customer = deserializer.deserialize(TOPIC, line.getBytes(StandardCharsets.UTF_8));
                } catch (SerializationException error) {
                    throw new IOException("Invalid customer at " + path + " line " + lineNumber, error);
                }
                producer.send(new ProducerRecord<>(TOPIC, customer.id(), customer)).get();
            }
        }
    }
}
```

`customers.jsonl`에 `{"id":"c-101","name":"Kim"}`처럼 한 줄에 고객 JSON 객체 하나를 넣고, [03번의 토픽 생성 명령](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#2-토픽-생성과-설정-변경)으로 `customers.json.v1`을 만든다. `application.mainClass`를 `pizza.CustomerFilePublisher`로 지정한 뒤 `./gradlew :pizza-producer:run --args=/절대경로/customers.jsonl`을 실행한다. 컨슈머의 `key.deserializer`는 `StringDeserializer`, `value.deserializer`는 `CustomerFilePublisher.CustomerDeserializer.class.getName()`으로 설정한다.

파일 발행기는 각 전송의 결과를 기다리고, 파일 형식 오류를 만나면 경로와 줄 번호를 남기고 멈춘다. 먼저 성공한 줄은 이미 Kafka에 기록돼 있으므로, 같은 파일을 처음부터 다시 발행할 때는 중복 반영 가능성을 고려한다. [06번 · 멱등 전송의 보장 범위](06_kafka_producer_idempotence_and_transactions.md#1-멱등-프로듀서의-보장-범위)

## 3. 저장된 JSON을 읽을 수 있게 스키마를 바꾼다

예제의 `@JsonIgnoreProperties(ignoreUnknown = true)`는 새 필드를 추가한 값을 기존 컨슈머가 읽도록 허용한다. 새 컨슈머도 기존 레코드를 읽어야 하므로 새 필드는 선택 사항으로 두거나 누락 시 기본값을 정한다. 필수 필드명이나 타입을 바꾸는 경우에는 기존·신규 데이터를 읽는 경로를 준비하고, 보관 중인 레코드로 두 버전의 읽기 방향을 검증한다. 스키마 호환성을 관리하는 예는 [14번 Avro 실습](14_evolving_kafka_event_schemas_with_avro.md#2-호환성-방향과-배포-순서)에 있다.
