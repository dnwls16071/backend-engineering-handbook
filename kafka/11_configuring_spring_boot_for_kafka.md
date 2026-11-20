# Configuring Spring Boot for Kafka

Spring Boot는 `spring.kafka.*` 설정으로 브로커에 접속하고, 이벤트를 보낼 `KafkaTemplate`과 이벤트를 받을 리스너 컨테이너 팩토리를 구성한다. 여기서는 Java 17과 Spring Boot 4.0.2로 고객별 주문 이벤트를 주고받을 프로젝트를 준비한다. [Spring Boot · Apache Kafka Support](https://docs.spring.io/spring-boot/4.0/reference/messaging/kafka.html)

## 1. 프로젝트 의존성 선택하기

Maven 프로젝트의 부모를 `org.springframework.boot:spring-boot-starter-parent:4.0.2`로 지정하고 `<java.version>17</java.version>`을 설정한다. `spring-boot-maven-plugin`을 추가하면 `mvn spring-boot:run`으로 실행할 수 있다. 개별 라이브러리 버전은 Spring Boot의 의존성 관리에 맡긴다. [Spring Boot · Maven Plugin](https://docs.spring.io/spring-boot/4.0/maven-plugin/using.html) · [Spring Boot · Build Systems](https://docs.spring.io/spring-boot/4.0/reference/using/build-systems.html)

| 의존성 | 사용하는 곳 |
| --- | --- |
| `org.springframework.boot:spring-boot-starter-kafka` | `KafkaTemplate`, `@KafkaListener`, `KafkaAdmin`이 필요한 발행·구독 앱 |
| `org.springframework.boot:spring-boot-starter-webmvc` | 실습용 HTTP 발행·조회 API |
| `org.apache.kafka:kafka-streams` | DSL로 토픽 데이터를 변환하거나 집계하는 13번 실습부터 추가 |

Kafka Java 클라이언트를 직접 쓰면 `KafkaProducer`와 `KafkaConsumer`의 생성과 종료를 애플리케이션이 관리한다. Spring for Apache Kafka는 이 클라이언트 위에 템플릿과 리스너 컨테이너를 제공한다. Kafka Streams가 필요한 경우에는 집계 로직을 앱에 포함하고 Spring이 런타임 수명 주기를 관리하도록 구성할 수 있다. [Kafka Producer](04_developing_reliable_kafka_producer_applications.md) · [Kafka Consumer](05_developing_reliable_kafka_consumer_applications.md) · [Spring for Apache Kafka · Streams Support](https://docs.spring.io/spring-kafka/reference/4.0/streams.html)

## 2. 브로커 주소와 직렬화 설정하기

`src/main/resources/application.properties`에 다음 설정을 넣는다. 예제에서 레코드 키는 고객 ID, 값은 주문 이벤트 유형이며 둘 다 문자열이다. 기본 브로커 주소는 01번의 호스트 포트에 맞췄다. 다른 환경에서는 `KAFKA_BOOTSTRAP_SERVERS`로 바꾼다. [Kafka 클러스터 실습](01_apache_kafka_cluster_and_log_fundamentals.md) · [Spring Boot · Apache Kafka Support](https://docs.spring.io/spring-boot/4.0/reference/messaging/kafka.html)

```properties
spring.kafka.bootstrap-servers=${KAFKA_BOOTSTRAP_SERVERS:localhost:19092}
spring.kafka.producer.key-serializer=org.apache.kafka.common.serialization.StringSerializer
spring.kafka.producer.value-serializer=org.apache.kafka.common.serialization.StringSerializer
spring.kafka.consumer.key-deserializer=org.apache.kafka.common.serialization.StringDeserializer
spring.kafka.consumer.value-deserializer=org.apache.kafka.common.serialization.StringDeserializer
spring.kafka.consumer.group-id=study-order-audit
spring.kafka.consumer.auto-offset-reset=earliest
spring.kafka.consumer.enable-auto-commit=false
spring.kafka.listener.ack-mode=record
```

`spring.kafka.bootstrap-servers`는 공통 설정이고 `producer.*`, `consumer.*`, `listener.*`는 각각 적용 대상이 다르다. 브로커에 최초로 접속한 뒤에는 브로커가 알린 주소로 통신하므로, 연결이 계속 실패하면 실행 위치에서 `advertised.listeners`의 주소에 도달할 수 있는지 확인한다. [Kafka 리스너와 연결 설정](01_apache_kafka_cluster_and_log_fundamentals.md) · [Spring Boot · Additional Kafka Properties](https://docs.spring.io/spring-boot/4.0/reference/messaging/kafka.html#messaging.kafka.additional-properties)

## 3. `@Bean`으로 입력 토픽 정의하기

`src/main/java/example/kafka/OrderApplication.java`를 만든다. Spring Boot가 구성한 `KafkaAdmin`은 컨텍스트 초기화 시 `NewTopic` 빈으로 선언한 토픽을 준비한다. 파티션 한 개와 복제 계수 `1`은 단일 브로커 실습 설정이다. 운영 환경에서는 토픽 관리 권한과 클러스터 정책에 맞춰 생성 방법을 정한다. [Spring for Apache Kafka · Configuring Topics](https://docs.spring.io/spring-kafka/reference/kafka/configuring-topics.html)

```java
package example.kafka;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.kafka.config.TopicBuilder;

@SpringBootApplication
public class OrderApplication {
    static final String ORDER_EVENTS = "study.order-events.v1";

    public static void main(String[] args) {
        SpringApplication.run(OrderApplication.class, args);
    }

    @Bean
    NewTopic orderEventsTopic() {
        return TopicBuilder.name(ORDER_EVENTS).partitions(1).replicas(1).build();
    }
}
```

연결과 직렬화처럼 배포 환경에 따라 바뀌는 값은 프로퍼티로 관리한다. 서로 다른 설정으로 두 리스너를 운영해야 한다면 추가 팩토리를 빈으로 등록하고 `@KafkaListener(containerFactory = "빈이름")`에서 선택할 수 있다. 기본 컨테이너 팩토리를 직접 대체할 때는 커밋과 오류 처리 설정도 함께 구성한다. [Spring for Apache Kafka · @KafkaListener](https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/listener-annotation.html)

## 4. 다음 단계

브로커를 시작한 뒤 `mvn spring-boot:run`으로 앱을 띄우고 Kafka CLI로 `study.order-events.v1` 토픽이 있는지 확인한다. 이 구성을 그대로 사용해 HTTP 요청에서 이벤트를 발행하고 리스너에서 수신한다. [Kafka CLI](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md) · [Producing and Consuming Events with Spring Kafka](12_producing_and_consuming_events_with_spring_kafka.md)
