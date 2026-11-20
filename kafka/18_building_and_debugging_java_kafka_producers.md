# Building and Debugging Java Kafka Producers

Java 17과 Kafka 클라이언트 4.3.2로 피자 주문을 발행한다. 주문 ID를 키로 사용해 같은 주문의 상태 변경이 같은 파티션에 기록되는지 살펴보고, 레코드마다 응답을 기다리는 방식과 콜백으로 결과를 받는 방식을 비교한다. [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 1. Gradle 멀티 프로젝트를 구성한다

새 실습 디렉터리의 `settings.gradle`에 모듈을 등록한다. `pizza-domain`은 주문 타입을 정의하고 `pizza-producer`는 그 타입과 Kafka 클라이언트를 사용한다. [Gradle · Multi-Project Builds](https://docs.gradle.org/current/userguide/multi_project_builds.html)

```groovy
rootProject.name = 'pizza-kafka-lab'
include 'pizza-domain', 'pizza-producer'
```

루트 `build.gradle`에서 두 모듈의 Java 툴체인을 17로 맞춘다. 두 모듈 디렉터리를 만든 뒤 IntelliJ IDEA에서 루트를 Gradle 프로젝트로 열어 동기화한다. Gradle JVM에는 Wrapper 버전이 지원하는 JDK를 지정한다. Wrapper가 없다면 설치된 Gradle에서 `gradle wrapper`를 실행해 생성한다. [Gradle · Java Toolchains](https://docs.gradle.org/current/userguide/toolchains.html) · [JetBrains · Gradle](https://www.jetbrains.com/help/idea/gradle.html)

```groovy
subprojects {
    apply plugin: 'java'
    java { toolchain { languageVersion = JavaLanguageVersion.of(17) } }
    repositories { mavenCentral() }
}

project(':pizza-producer') {
    apply plugin: 'application'
    dependencies {
        implementation project(':pizza-domain')
        implementation 'org.apache.kafka:kafka-clients:4.3.2'
    }
    application { mainClass = 'pizza.PizzaProducer' }
}
```

## 2. 피자 주문의 생성과 조리를 발행한다

`pizza-domain/src/main/java/pizza/PizzaOrder.java`에 주문 타입을 둔다.

```java
package pizza;

public record PizzaOrder(long id, String menu) {}
```

`pizza-producer/src/main/java/pizza/PizzaProducer.java`는 주문마다 `CREATED`, `BAKED` 순서로 보낸다. 키의 Java 타입이 `Long`이므로 `LongSerializer`를, 문자열 값에는 `StringSerializer`를 사용한다. 읽을 때도 키에 `LongDeserializer`를 사용한다. 기본 키 라우팅은 직렬화된 바이트를 해시하므로 키를 문자열로 바꾸면 같은 주문 번호라도 파티션이 달라질 수 있다. [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [LongSerializer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/serialization/LongSerializer.html)

```java
package pizza;

import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.Future;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.serialization.LongSerializer;
import org.apache.kafka.common.serialization.StringSerializer;

public class PizzaProducer {
    public static void main(String[] args) throws Exception {
        boolean sync = args.length > 0 && args[0].equals("sync");
        var config = new Properties();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, LongSerializer.class.getName());
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        var orders = List.of(new PizzaOrder(101, "margherita"), new PizzaOrder(102, "pepperoni"));

        try (var producer = new KafkaProducer<Long, String>(config)) {
            var pending = new ArrayList<Future<RecordMetadata>>();
            for (var order : orders) {
                for (String status : List.of("CREATED", "BAKED")) {
                    var record = new ProducerRecord<>("pizza.orders.v1", order.id(),
                            order.menu() + "," + status);
                    if (sync) {
                        report(order.id(), status, producer.send(record).get());
                    } else {
                        pending.add(producer.send(record, (metadata, error) -> {
                            if (error == null) {
                                report(order.id(), status, metadata);
                            } else {
                                System.err.printf("order=%d status=%s failed: %s%n", order.id(), status, error);
                            }
                        }));
                    }
                }
            }
            for (var future : pending) {
                future.get();
            }
        }
    }

    private static void report(long orderId, String status, RecordMetadata metadata) {
        System.out.printf("order=%d status=%s partition=%d offset=%d%n",
                orderId, status, metadata.partition(), metadata.offset());
    }
}
```

[01번 Docker Kafka](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)를 실행하고 [03번의 토픽 생성 명령](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#2-토픽-생성과-설정-변경)으로 `pizza.orders.v1`을 파티션 세 개로 만든다. `./gradlew :pizza-producer:run --args=sync`는 매 레코드의 응답을 기다리고, `./gradlew :pizza-producer:run`은 모든 전송을 먼저 제출한다. 비동기 실행도 마지막에 `Future.get()`으로 결과를 확인하며, 실패하면 예외의 원인이 `ExecutionException`에 담겨 호출자에게 전달된다. 두 방식에서 주문 ID별로 파티션이 같고 `BAKED`의 오프셋이 `CREATED`보다 큰지 확인한다.

## 3. 제출 시점과 완료 시점을 디버깅한다

1. IntelliJ에서 `PizzaProducer.main`을 Debug로 실행하고 `var record` 다음 줄에 중단점을 둔다. `record.topic()`, `record.key()`, `record.value()`로 토픽과 키 타입, 이벤트 내용을 확인한다.
2. 실행 구성의 프로그램 인수에 `sync`를 넣으면 `get()`에서 현재 전송이 완료될 때까지 기다린다. 인수를 빼고 실행한 뒤 콜백 안에서 `metadata.partition()`, `metadata.offset()` 또는 `error`를 관찰한다. 콜백은 보통 프로듀서의 I/O 스레드에서 실행되며, 이 스레드를 오래 멈추면 타임아웃에 영향을 줄 수 있다. 실행을 계속하며 값을 보려면 로그 중단점을 사용한다.
3. `send()`도 토픽 메타데이터나 버퍼가 부족하면 대기할 수 있고, 직렬화 오류처럼 호출 시점에 드러나는 실패가 있다. 응답이 늦을 때는 `send()` 안에서 대기하는지, 반환된 Future의 완료를 기다리는지부터 확인한다. [JetBrains · Breakpoints](https://www.jetbrains.com/help/idea/using-breakpoints.html) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
