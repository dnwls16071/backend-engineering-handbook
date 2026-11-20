# Building and Querying Kafka Streams Topologies

Kafka Streams는 앱 프로세스에 포함하는 Java 라이브러리다. 별도의 스트림 처리 클러스터 없이 기존 Kafka 브로커를 사용하고, 앱 인스턴스 간에 입력 파티션 단위로 작업을 나눈다. 12번의 주문 이벤트에서 `PLACED`만 골라 고객별 누적 건수를 만들고, Spring MVC API에서 로컬 상태를 조회한다. [Apache Kafka · Streams Architecture](https://kafka.apache.org/41/streams/architecture/) · [Producing and Consuming Events with Spring Kafka](12_producing_and_consuming_events_with_spring_kafka.md)

## 1. DSL로 집계 토폴로지 정의하기

11번 프로젝트에 `org.apache.kafka:kafka-streams`를 추가한다. `application.properties`에 `spring.kafka.streams.application-id=study-order-counts-v1`을 넣고, 단일 브로커에서는 `spring.kafka.streams.properties[replication.factor]=1`을 설정한다. `@EnableKafkaStreams`로 활성화하면 Spring Boot가 설정 빈을 구성하고, `StreamsBuilderFactoryBean`이 `KafkaStreams`를 시작하고 종료한다. [Spring Boot · Kafka Streams](https://docs.spring.io/spring-boot/4.0/reference/messaging/kafka.html#messaging.kafka.streams)

`src/main/java/example/kafka/OrderStreamsConfiguration.java`를 추가한다. `stream()`으로 입력 토픽을 읽고, `filter()`로 집계할 이벤트를 고르고, `groupByKey().count()`로 상태를 갱신한다. `Materialized.as()`는 상태 저장소에 조회용 이름을 붙인다. 문자열 키를 그대로 사용하므로 키 변경에 따른 재파티셔닝이 필요 없다. 값 변환에는 `mapValues()`, 출력 토픽으로 결과를 보낼 때는 `to()`를 사용한다. [Apache Kafka · Streams DSL](https://kafka.apache.org/41/streams/developer-guide/dsl-api/) · [07번 Kafka Streams 조인과 윈도우](07_kafka_streams_dsl_joins_and_stateful_processing.md)

```java
package example.kafka;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.KTable;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.state.KeyValueStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafkaStreams;

@Configuration(proxyBeanMethods = false)
@EnableKafkaStreams
public class OrderStreamsConfiguration {
    static final String COUNT_STORE = "placed-order-counts";

    @Bean
    KTable<String, Long> orderCounts(StreamsBuilder builder) {
        return builder.stream(OrderApplication.ORDER_EVENTS, Consumed.with(Serdes.String(), Serdes.String()))
                .filter((customerId, type) -> customerId != null && "PLACED".equals(type))
                .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
                .count(Materialized.<String, Long, KeyValueStore<Bytes, byte[]>>as(COUNT_STORE)
                        .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()));
    }
}
```

## 2. Interactive Queries를 HTTP로 열기

`src/main/java/example/kafka/OrderCountController.java`를 추가한다. `KafkaStreams.store()`에 이름과 타입을 전달하면 현재 인스턴스의 읽기 전용 저장소를 얻는다. 단일 인스턴스 실습에서 준비된 저장소에 해당 키가 없으면 `404`, 시작 또는 리밸런싱 중 저장소를 조회할 수 없으면 `503`을 반환한다. [Apache Kafka · Interactive Queries](https://kafka.apache.org/41/streams/developer-guide/interactive-queries/)

```java
package example.kafka;

import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StoreQueryParameters;
import org.apache.kafka.streams.errors.InvalidStateStoreException;
import org.apache.kafka.streams.state.QueryableStoreTypes;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.config.StreamsBuilderFactoryBean;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderCountController {
    private final StreamsBuilderFactoryBean streamsFactory;

    OrderCountController(StreamsBuilderFactoryBean streamsFactory) {
        this.streamsFactory = streamsFactory;
    }

    @GetMapping("/customers/{customerId}/placed-order-count")
    ResponseEntity<Long> count(@PathVariable("customerId") String customerId) {
        KafkaStreams streams = streamsFactory.getKafkaStreams();
        if (streams == null || streams.state() != KafkaStreams.State.RUNNING) {
            return ResponseEntity.status(503).build();
        }
        try {
            var store = streams.store(StoreQueryParameters.fromNameAndType(
                    OrderStreamsConfiguration.COUNT_STORE, QueryableStoreTypes.<String, Long>keyValueStore()));
            return ResponseEntity.ofNullable(store.get(customerId));
        } catch (InvalidStateStoreException e) {
            return ResponseEntity.status(503).build();
        }
    }
}
```

여러 인스턴스를 운영할 때는 인스턴스마다 `application.server`에 조회 가능한 주소를 설정한다. `queryMetadataForKey()` 또는 Spring의 `KafkaStreamsInteractiveQueryService`로 키를 담당하는 활성 호스트를 찾고, 앱이 그 호스트에 HTTP 요청을 전달한다. 리밸런싱으로 소유자가 바뀌면 메타데이터를 다시 조회한다. [Spring for Apache Kafka · Interactive Query Support](https://docs.spring.io/spring-kafka/reference/4.0/streams.html#interactive-query-support)

## 3. 집계와 조회 확인하기

앱을 재시작하고, 12번의 발행 API로 새 고객 키에 `PLACED`, `CANCELLED`, `PLACED`를 순서대로 전송한다. `GET /customers/{customerId}/placed-order-count`에서 처리 완료 후 `2`를 확인한다. 발행 직후에는 상태 저장소가 이전 값을 반환할 수 있다. `kafka-streams-test-utils`의 `TopologyTestDriver`로 같은 입력을 주고 저장소의 값을 검사하면 브로커 없이 필터와 집계를 검증할 수 있다. [Apache Kafka · Testing a Streams Application](https://kafka.apache.org/41/streams/developer-guide/testing/)

내장 KRaft 브로커에서 조회 API가 `2`를 반환했다. `TopologyTestDriver`에서도 고객 키별로 `PLACED` 이벤트만 집계됐다.
