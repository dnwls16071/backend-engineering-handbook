# Kafka Streams DSL, Joins, and Stateful Processing

Kafka Streams는 Kafka 토픽의 레코드를 지속적으로 읽고 변환, 조인, 집계하는 JVM 라이브러리다. 주문 이벤트에 고객 등급과 지역 이름을 붙이고, 고객별 1분 주문 수를 로컬 상태 저장소에서 조회하는 흐름으로 주요 기능을 살펴본다. [Apache Kafka · Streams Architecture](https://kafka.apache.org/43/streams/architecture/)

## 1. 처리 토폴로지와 주요 설정

Streams DSL에서 `stream()`과 `table()`로 입력을 정의하고, `filter()`, `mapValues()`, `join()`, `groupByKey()`로 처리 단계를 연결한다. `to()`는 처리 결과를 Kafka 토픽으로 보낸다. 이 연결이 토폴로지를 이루며, Kafka Streams는 입력 파티션을 바탕으로 작업을 나눠 같은 애플리케이션의 스레드와 인스턴스에 배정한다. [Apache Kafka · Streams DSL](https://kafka.apache.org/43/streams/developer-guide/dsl-api/) · [Apache Kafka · Streams Architecture](https://kafka.apache.org/43/streams/architecture/)

| 설정 | 적용 기준 |
| --- | --- |
| `application.id` | 같은 토폴로지의 복제 인스턴스에 같은 ID를 사용한다. 컨슈머 그룹과 내부 토픽, 로컬 상태의 이름을 정하는 데 사용된다. |
| `bootstrap.servers` | 클라이언트가 최초로 접속할 Kafka 브로커 주소를 지정한다. |
| `default.key.serde`, `default.value.serde` | 기본 직렬화·역직렬화 방식을 지정한다. 단계별 타입이 달라지면 해당 연산에 Serde를 전달한다. |
| `num.stream.threads` | 인스턴스에서 작업을 처리할 스트림 스레드 수를 정한다. 실제 병렬 처리량은 배정할 작업 수의 제약을 받는다. |
| `state.dir`, `num.standby.replicas` | 로컬 상태 위치와 복구에 사용할 대기 상태 복제본 수를 정한다. |
| `processing.guarantee` | 기본 `at_least_once`에서는 복구 중 재처리가 일어날 수 있다. `exactly_once_v2`는 Kafka 출력, 상태 변경 로그, 입력 오프셋의 커밋에 트랜잭션을 적용한다. |

분산 실행에서는 인스턴스마다 별도의 로컬 상태 디렉터리를 사용한다. Kafka 트랜잭션의 처리 보장 범위는 06번 문서에서 확인할 수 있다. [Apache Kafka · Streams Configs](https://kafka.apache.org/43/streams/developer-guide/config-streams/) · [Kafka Producer Idempotence and Transactions](06_kafka_producer_idempotence_and_transactions.md)

## 2. KStream, KTable, GlobalKTable과 조인

| 모델 | 레코드 해석 | 상태 배치 |
| --- | --- | --- |
| `KStream` | 주문 발생처럼 키가 같아도 각각 독립적인 이벤트다. | 상태는 조인이나 집계처럼 필요한 연산이 유지한다. |
| `KTable` | 키별 값의 변경이다. 일반 테이블에서 같은 키의 새 값은 기존 값을 갱신하고, null 값은 삭제를 뜻한다. | 인스턴스별로 담당 파티션의 상태를 나눠 가진다. |
| `GlobalKTable` | 테이블 형태로 읽으며 키로 조회할 수 있다. | 모든 인스턴스가 입력 토픽의 모든 파티션을 읽어 전체 테이블을 보유한다. |

`KStream–KTable` 키 조인은 주문 키로 고객 등급을 조회한다. 양쪽의 파티션 수와 조인 키의 파티셔닝 방식이 일치해야 같은 키가 같은 작업에서 만난다. 스트림의 키를 바꾼 경우 조인 전에 재파티셔닝이 필요할 수 있다. 조인 결과는 스트림 레코드가 들어올 때 생성된다. 고객 등급이 갱신돼도 과거 주문을 다시 조인하지 않는다. 아래 예제는 일반 `KTable`이고, 버전드 상태 저장소를 사용하는 경우에는 레코드 시각 기준 조회도 가능하다. [Apache Kafka · Streams DSL Joins](https://kafka.apache.org/43/streams/developer-guide/dsl-api/#joining)

`KStream–GlobalKTable` 조인은 매퍼로 주문 값에서 지역 코드를 꺼내 지역 테이블을 조회한다. 결과는 원래 스트림 키인 고객 ID를 유지한다. 전체 테이블을 각 인스턴스에 복제하므로 이 조인을 위한 코파티셔닝이 필요 없다. 인스턴스별 저장 공간과 시작 시 테이블 로딩 비용이 생기며, 글로벌 테이블 갱신과 스트림 레코드 처리는 이벤트 시각으로 동기화되지 않는다. [Apache Kafka · Streams DSL Joins](https://kafka.apache.org/43/streams/developer-guide/dsl-api/#joining)

## 3. 윈도우와 Interactive Queries

`windowedBy()`는 이벤트 시각으로 집계 범위를 나눈다. 텀블링 윈도우는 겹치지 않는 고정 구간을, 호핑 윈도우는 일정한 간격으로 시작하는 겹치는 구간을 만든다. 슬라이딩 윈도우는 이벤트 시각 차이를 기준으로 묶으며, 세션 윈도우는 같은 키의 이벤트가 일정 시간 들어오지 않으면 세션을 구분한다. 예제는 1분 텀블링 윈도우에 10초의 지연 허용 구간을 둔다. 스트림 시간은 처리한 레코드의 시각으로 진행하며, 윈도우 종료 시각과 지연 허용 구간을 기준으로 늦게 도착한 레코드를 집계할지 결정한다. [Apache Kafka · Streams DSL Windowing](https://kafka.apache.org/43/streams/developer-guide/dsl-api/#windowing)

`Materialized.as()`로 이름을 붙인 저장소는 `KafkaStreams.store()`와 `QueryableStoreTypes`로 로컬에서 조회한다. 여러 인스턴스가 상태를 나눠 보유하는 경우, 조회할 키의 소유 인스턴스를 메타데이터로 찾아 애플리케이션의 HTTP 또는 RPC 계층으로 요청을 전달한다. `application.server`는 해당 인스턴스의 조회 주소를 메타데이터에 등록하는 설정이다. [Apache Kafka · Interactive Queries](https://kafka.apache.org/43/streams/developer-guide/interactive-queries/)

## 4. Docker에서 주문 조인과 윈도우 집계 확인하기

01번의 Docker Kafka가 실행 중인 디렉터리에서 네 토픽을 만든다. 고객 등급과 지역 이름을 먼저 발행한다. 주문 레코드의 값은 `주문 ID|지역 코드|이벤트 시각(밀리초)` 형식이다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)

```bash
for topic in streams.orders.v1 streams.customers.v1 streams.regions.v1 streams.enriched.v1; do
  docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:29092 --create --topic "$topic" \
    --partitions 1 --replication-factor 1
done

publish() {
  local topic="$1"
  shift
  printf '%s\n' "$@" |
    docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
      --bootstrap-server kafka:29092 --topic "$topic" \
      --reader-property parse.key=true --reader-property key.separator=:
}

publish streams.customers.v1 'c-1:gold'
publish streams.regions.v1 'seoul:KR-Seoul'
```

아래 코드를 `OrderStreams.java`로 저장한다. 앱은 고객 테이블이 조회 가능한 시점에 `ready`를 출력하고, 주문 두 건이 같은 윈도우에 반영되면 조회 결과를 출력한 뒤 종료한다. 이벤트 시각은 실습 데이터를 다시 만들어도 같은 윈도우에 들어가도록 주문 값에서 읽는다.

```java
import java.time.Duration;
import java.time.Instant;
import java.util.Properties;
import java.util.function.BooleanSupplier;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StoreQueryParameters;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.errors.InvalidStateStoreException;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.apache.kafka.streams.state.QueryableStoreTypes;
import org.apache.kafka.streams.state.WindowStore;

public class OrderStreams {
    private static final Instant WINDOW_START = Instant.parse("2025-01-01T00:00:00Z");

    public static void main(String[] args) throws InterruptedException {
        var builder = new StreamsBuilder();
        var orders = builder.stream("streams.orders.v1", Consumed.with(Serdes.String(), Serdes.String())
                .withTimestampExtractor((record, partitionTime) -> {
                    String order = (String) record.value();
                    return Long.parseLong(order.substring(order.lastIndexOf('|') + 1));
                }))
                .mapValues(order -> order.substring(0, order.lastIndexOf('|')));
        var customers = builder.<String, String>table("streams.customers.v1", Materialized.as("customers"));
        var regions = builder.<String, String>globalTable("streams.regions.v1");

        var enriched = orders.join(customers, (order, tier) -> order + "|" + tier)
                .join(regions, (customerId, order) -> order.split("[|]")[1],
                        (order, region) -> order + "|" + region);
        enriched.to("streams.enriched.v1");
        enriched.groupByKey()
                .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(1), Duration.ofSeconds(10)))
                .count(Materialized.<String, Long, WindowStore<Bytes, byte[]>>as("order-counts")
                        .withKeySerde(Serdes.String()).withValueSerde(Serdes.Long()));

        var config = new Properties();
        config.put(StreamsConfig.APPLICATION_ID_CONFIG, "order-streams-demo");
        config.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:19092");
        config.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        config.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        config.put(StreamsConfig.STATE_DIR_CONFIG, "stream-state");
        config.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, 1);

        try (var streams = new KafkaStreams(builder.build(), config)) {
            streams.start();
            await(() -> {
                var store = streams.store(StoreQueryParameters.fromNameAndType(
                        "customers", QueryableStoreTypes.<String, String>keyValueStore()));
                return "gold".equals(store.get("c-1"));
            });
            System.out.println("ready");

            await(() -> {
                var store = streams.store(StoreQueryParameters.fromNameAndType(
                        "order-counts", QueryableStoreTypes.<String, Long>windowStore()));
                return Long.valueOf(2).equals(store.fetch("c-1", WINDOW_START.toEpochMilli()));
            });
            System.out.printf("customer=c-1 window=%s count=2%n", WINDOW_START);
        }
    }

    private static void await(BooleanSupplier ready) throws InterruptedException {
        long deadline = System.nanoTime() + Duration.ofSeconds(45).toNanos();
        do {
            try {
                if (ready.getAsBoolean()) {
                    return;
                }
            } catch (InvalidStateStoreException ignored) {
                // The local store may still be restoring.
            }
            Thread.sleep(100);
        } while (System.nanoTime() < deadline);
        throw new IllegalStateException("Timed out waiting for the demo state");
    }
}
```

JDK 17 이상을 사용한다. 실행 중인 컨테이너에서 Kafka Streams와 상태 저장소에 필요한 라이브러리를 복사한다. 아래 명령은 같은 셸에서 앱이 준비되면 주문 두 건을 발행한다. 처음 실행할 때는 새 토픽과 상태 디렉터리를 사용한다.

```bash
mkdir -p lib
docker compose cp kafka:/opt/kafka/libs/. ./lib
javac -cp 'lib/*' OrderStreams.java
java -cp '.:lib/*' OrderStreams > streams.log 2>&1 &
streams_pid=$!

until rg -q '^ready$' streams.log; do
  if ! kill -0 "$streams_pid" 2>/dev/null; then
    cat streams.log
    break
  fi
  sleep 1
done

if rg -q '^ready$' streams.log; then
  publish streams.orders.v1 'c-1:o-1|seoul|1735689605000' 'c-1:o-2|seoul|1735689620000'
fi
wait "$streams_pid"
rg '^customer=' streams.log

docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic streams.enriched.v1 \
  --partition 0 --from-beginning --timeout-ms 10000 --max-messages 2 \
  --formatter-property print.key=true
```

Kafka 4.3.2에서 `2025-01-01T00:00:00Z`에 시작한 윈도우의 고객 `c-1` 집계가 `2`로 조회됐다. 출력 토픽에서는 주문 두 건 모두 고객 등급 `gold`와 지역 이름 `KR-Seoul`이 붙은 상태로 읽혔다.

## 5. Processor API와 Spark Structured Streaming

Processor API는 `process()`에서 레코드를 직접 처리하고, `ProcessorContext`로 다음 노드에 전달하거나 연결된 상태 저장소에 접근한다. `schedule()`을 통해 스트림 시간 또는 벽시계 기준으로 주기 작업도 등록할 수 있다. 일반 조인과 집계는 DSL 연산으로 표현하고, 레코드별 상태 갱신이나 만료 시점의 로직이 필요한 곳에 Processor API를 결합할 수 있다. [Apache Kafka · Processor API](https://kafka.apache.org/43/streams/developer-guide/processor-api/)

| 비교 항목 | Kafka Streams | Spark Structured Streaming |
| --- | --- | --- |
| 실행 모델 | JVM 애플리케이션 인스턴스에서 Kafka 파티션 기반 작업을 실행한다. | Spark에서 DataFrame·Dataset 쿼리를 실행한다. 기본 엔진은 마이크로배치다. |
| 데이터 입출력 | Kafka 토픽 중심으로 처리하고, 로컬 상태와 Kafka 내부 토픽을 활용한다. | Kafka와 파일 등 여러 소스·싱크를 연결하고 체크포인트를 사용한다. |
| 이벤트 시간 | 타임스탬프 추출기, 윈도우, 지연 허용 구간을 조합한다. | 이벤트 시간 컬럼과 워터마크를 사용해 늦은 데이터와 상태 보존을 관리한다. |
| 어울리는 작업 | 서비스에서 Kafka 이벤트 보강, 라우팅, 증분 집계를 실행할 때 적합하다. | Spark 기반 데이터 파이프라인에서 여러 소스를 결합하거나 SQL 중심으로 스트리밍 데이터를 처리할 때 적합하다. |

[Apache Kafka · Streams Architecture](https://kafka.apache.org/43/streams/architecture/) · [Apache Spark · Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/streaming/index.html) · [Apache Spark · DataFrame and Dataset APIs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
