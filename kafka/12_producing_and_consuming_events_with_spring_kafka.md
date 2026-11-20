# Producing and Consuming Events with Spring Kafka

주문 이벤트를 HTTP로 받아 `KafkaTemplate`으로 발행하고, 같은 토픽을 구독하는 `@KafkaListener`에서 처리한다. 11번의 Spring Boot 프로젝트를 사용하며 키는 고객 ID, 값은 `PLACED`나 `CANCELLED` 같은 주문 이벤트 유형이다. [Configuring Spring Boot for Kafka](11_configuring_spring_boot_for_kafka.md)

## 1. `KafkaTemplate`으로 이벤트 발행하기

`send(topic, key, value)`는 `CompletableFuture<SendResult<K, V>>`를 반환한다. 아래 컨트롤러는 전송 결과가 성공하면 Kafka가 반환한 파티션과 오프셋을 돌려준다. 이 시점에는 리스너 처리가 아직 진행 중일 수 있다. 실패는 future를 통해 HTTP 요청 처리 계층으로 전달되며, 브로커 확인 수준과 재시도 정책은 Producer 설정에 따른다. [Spring for Apache Kafka · Sending Messages](https://docs.spring.io/spring-kafka/reference/kafka/sending-messages.html) · [Kafka Producer 설정](04_developing_reliable_kafka_producer_applications.md)

`src/main/java/example/kafka/OrderEventController.java`를 추가한다.

```java
package example.kafka;

import java.util.concurrent.CompletableFuture;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderEventController {
    private final KafkaTemplate<String, String> template;

    OrderEventController(KafkaTemplate<String, String> template) {
        this.template = template;
    }

    @PostMapping(path = "/customers/{customerId}/order-events", consumes = "text/plain")
    CompletableFuture<PublishedEvent> publish(@PathVariable("customerId") String customerId,
                                              @RequestBody String eventType) {
        return template.send(OrderApplication.ORDER_EVENTS, customerId, eventType)
                .thenApply(result -> {
                    var metadata = result.getRecordMetadata();
                    return new PublishedEvent(metadata.partition(), metadata.offset());
                });
    }

    record PublishedEvent(int partition, long offset) {}
}
```

## 2. `@KafkaListener`로 이벤트 구독하기

리스너 컨테이너가 그룹 가입과 `poll()`을 담당하고, 역직렬화한 레코드를 메서드에 전달한다. `ConsumerRecord`를 받으면 값과 키 외에 파티션과 오프셋도 사용할 수 있다. 여기서는 11번에 설정한 `study-order-audit` 그룹 ID를 사용한다. [Spring for Apache Kafka · @KafkaListener](https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/listener-annotation.html)

`src/main/java/example/kafka/OrderAuditListener.java`를 추가한다.

```java
package example.kafka;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class OrderAuditListener {
    private static final Logger log = LoggerFactory.getLogger(OrderAuditListener.class);

    @KafkaListener(topics = OrderApplication.ORDER_EVENTS)
    void audit(ConsumerRecord<String, String> event) {
        log.info("customer={} type={} partition={} offset={}",
                event.key(), event.value(), event.partition(), event.offset());
    }
}
```

`enable-auto-commit=false`와 `ack-mode=record`에서는 리스너가 처리를 마치고 정상적으로 반환한 뒤 컨테이너가 오프셋을 커밋한다. 실패를 컨테이너가 감지하려면 리스너 밖으로 예외를 전파한다. 처리 완료 후 커밋 전에 앱이 중단되면 같은 레코드를 다시 받을 수 있으므로, DB 저장처럼 부수 효과가 있는 작업은 중복 실행을 고려한다. `earliest`는 유효한 커밋 오프셋이 없을 때 적용된다. [Spring for Apache Kafka · Listener Containers](https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html) · [Spring for Apache Kafka · Handling Exceptions](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html) · [Kafka Consumer 오프셋과 재처리](05_developing_reliable_kafka_consumer_applications.md)

## 3. 발행 결과와 수신 로그 확인하기

브로커와 앱이 실행 중일 때 다음 요청을 보낸다. HTTP 응답의 `partition`과 `offset`이 `customer=c-1 type=PLACED` 수신 로그에 찍힌 값과 일치하는지 확인한다.

```bash
curl --fail-with-body -H 'Content-Type: text/plain' --data 'PLACED' \
  http://localhost:8080/customers/c-1/order-events
```

CLI에서 `study-order-audit` 그룹의 오프셋도 확인할 수 있다. 그룹에 같은 토픽을 구독하는 앱을 추가하면 파티션을 나눠 처리하고, 별도 그룹에 속한 구독자는 각자 진행 위치를 유지한다. Kafka 안에서 읽기·처리·발행을 하나의 트랜잭션으로 묶는 흐름은 06번에서 다룬다. [Kafka CLI](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md) · [Kafka Producer Idempotence and Transactions](06_kafka_producer_idempotence_and_transactions.md)

내장 KRaft 브로커에서 이벤트 세 건을 발행했다. 리스너는 파티션 `0`의 오프셋 `0`부터 `2`까지 읽었고, 그룹에 다음 오프셋 `3`이 커밋됐다.
