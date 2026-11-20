# Consuming Kafka Events into PostgreSQL

23번 프로듀서가 발행한 피자 주문 이벤트를 PostgreSQL에 저장한다. 컨슈머는 DB 트랜잭션을 커밋한 뒤 Kafka 오프셋을 커밋한다. 그 사이에 프로세스가 중단되면 같은 레코드를 다시 읽을 수 있으므로, `event_id`에 기본키를 두고 동일 이벤트의 재반영을 막는다. [파일 이벤트 발행](23_publishing_file_events_to_kafka.md) · [Apache Kafka · Message Delivery Semantics](https://kafka.apache.org/43/design/design/#message-delivery-semantics) · [PostgreSQL · INSERT](https://www.postgresql.org/docs/17/sql-insert.html)

## 1. 수신 루프와 저장 책임을 나눈다

공통 소비 코드에서 구독, `poll()`, 종료, 오프셋 커밋을 맡고, 처리 모듈에서 레코드 검증과 JDBC 저장을 맡긴다. DB 저장에 실패하면 롤백하고 예외를 소비 루프까지 전달한다. DB에는 반영됐지만 Kafka 커밋이 완료되지 않았다면 같은 `event_id`를 다시 처리해도 해당 행은 하나로 유지된다. 주문의 인벤토리나 잔액도 갱신하는 서비스라면 이벤트의 중복 확인과 상태 변경을 같은 DB 트랜잭션으로 묶는다. [Kafka Consumer 수명 주기](05_developing_reliable_kafka_consumer_applications.md) · [PostgreSQL JDBC · Connection Parameters](https://jdbc.postgresql.org/documentation/use/)

## 2. 로컬 DB와 연결을 준비한다

Kafka와 같은 디렉터리에 `compose.postgres.yaml`을 저장한다. 아래 계정과 비밀번호는 로컬 실습용이다. JDBC는 호스트의 루프백 포트 `15433`으로 접속한다. [Docker 공식 PostgreSQL 이미지](https://hub.docker.com/_/postgres)

```yaml
services:
  postgres:
    image: postgres:17-alpine
    ports:
      - "127.0.0.1:15433:5432"
    environment:
      POSTGRES_DB: orders
      POSTGRES_USER: orders
      POSTGRES_PASSWORD: orders-local
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "orders", "-d", "orders"]
      interval: 2s
      timeout: 3s
      retries: 20
```

```bash
orders_compose() {
  docker compose -f compose.yaml -f compose.postgres.yaml "$@"
}

orders_compose up -d --wait postgres
orders_compose exec -T postgres psql -U orders -d orders -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS pizza_order_event (
    event_id text PRIMARY KEY,
    order_id text NOT NULL,
    status text NOT NULL
);
SQL

mvn dependency:copy -Dartifact=org.postgresql:postgresql:42.7.11 -DoutputDirectory=lib
export PIZZA_DB_URL='jdbc:postgresql://127.0.0.1:15433/orders?connectTimeout=5&socketTimeout=10'
export PIZZA_DB_USER=orders
export PIZZA_DB_PASSWORD=orders-local
```

## 3. PostgreSQL 저장 후 Kafka 위치를 확정한다

`PostgresOrderConsumer.java`를 23번의 `FileOrderProducer.java` 옆에 저장한다. 예제는 검증을 위해 실행마다 최대 한 건을 받아 종료한다. `--leave-uncommitted`는 DB 커밋과 Kafka 커밋 사이에서 종료되는 상황을 만든다. 일반 실행에서는 `records.nextOffsets()`로 다음 읽기 위치를 커밋한다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [Apache Kafka · ConsumerRecords](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRecords.html)

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.time.Duration;
import java.util.List;
import java.util.Properties;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;

public class PostgresOrderConsumer {
    public static void main(String[] args) throws SQLException {
        if (args.length > 1 || (args.length == 1 && !args[0].equals("--leave-uncommitted"))) {
            throw new IllegalArgumentException("Usage: PostgresOrderConsumer [--leave-uncommitted]");
        }
        var config = new Properties();
        config.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,
                System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"));
        config.put(ConsumerConfig.GROUP_ID_CONFIG, "pizza-file-to-postgres");
        config.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        config.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        config.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        config.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        config.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, "1");

        try (var db = DriverManager.getConnection(System.getenv("PIZZA_DB_URL"),
                System.getenv("PIZZA_DB_USER"), System.getenv("PIZZA_DB_PASSWORD"));
             var consumer = new KafkaConsumer<String, String>(config)) {
            db.setAutoCommit(false);
            consumer.subscribe(List.of(FileOrderProducer.TOPIC));
            long deadline = System.nanoTime() + Duration.ofSeconds(20).toNanos();
            do {
                var records = consumer.poll(Duration.ofMillis(500));
                if (records.isEmpty()) {
                    continue;
                }
                var record = records.iterator().next();
                var event = PizzaOrderEvent.parse(record.value());
                int inserted = persist(db, event);
                System.out.printf("event=%s offset=%d inserted=%d%n",
                        event.eventId(), record.offset(), inserted);
                if (args.length == 0) {
                    consumer.commitSync(records.nextOffsets());
                    System.out.println("committed=" + records.nextOffsets());
                }
                return;
            } while (System.nanoTime() < deadline);
            throw new IllegalStateException("No order event received");
        }
    }

    private static int persist(Connection db, PizzaOrderEvent event) throws SQLException {
        try (var statement = db.prepareStatement("""
                INSERT INTO pizza_order_event (event_id, order_id, status)
                VALUES (?, ?, ?) ON CONFLICT (event_id) DO NOTHING
                """)) {
            statement.setString(1, event.eventId());
            statement.setString(2, event.orderId());
            statement.setString(3, event.status());
            int inserted = statement.executeUpdate();
            db.commit();
            return inserted;
        } catch (SQLException failure) {
            try {
                db.rollback();
            } catch (SQLException rollbackFailure) {
                failure.addSuppressed(rollbackFailure);
            }
            throw failure;
        }
    }
}
```

## 4. 파일 추가부터 DB 재처리까지 확인한다

새 토픽·그룹·테이블로 시작한다. 23번 프로듀서를 `--follow`로 실행하고 첫 줄만 존재하는 상태에서 소비자를 실행한다. 첫 실행에서 `inserted=1`이 출력되면 같은 그룹으로 재시작한다. 이때 이벤트와 오프셋은 같고 `inserted=0`이 출력된다. 그 뒤 파일에 두 번째 줄을 추가하고 한 번 더 소비한다.

```bash
javac -cp 'lib/*' FileOrderProducer.java PostgresOrderConsumer.java
java -cp '.:lib/*' PostgresOrderConsumer --leave-uncommitted
java -cp '.:lib/*' PostgresOrderConsumer

printf '%s\n' 'evt-2|order-901|PAID' >> pizza-orders.txt
java -cp '.:lib/*' PostgresOrderConsumer

orders_compose exec -T postgres psql -U orders -d orders -v ON_ERROR_STOP=1 \
  -c 'SELECT event_id, order_id, status FROM pizza_order_event ORDER BY event_id'
```

결과에는 `evt-1`과 `evt-2`가 각각 한 행씩 있어야 한다. JDBC 연결만 점검할 때도 `PIZZA_DB_URL`과 동일한 주소·포트·DB 이름으로 붙어 `SELECT 1`을 실행한다. 운영에서는 한 번의 `poll()`로 받은 레코드 수와 DB 작업 시간을 `max.poll.interval.ms`에 맞추고, DB 확인과 Kafka 커밋 사이의 재처리를 계속 검증한다. [PostgreSQL JDBC · Connecting to the Database](https://jdbc.postgresql.org/documentation/use/) · [Kafka 오프셋 커밋과 재처리](22_controlling_kafka_consumer_offsets_and_replay.md)

Kafka 4.3.2와 PostgreSQL 17에서 첫 실행은 `evt-1`을 저장했다. 같은 그룹으로 재시작하자 같은 오프셋을 다시 읽었고 `inserted=0`으로 확인됐다. 파일에 추가한 `evt-2`까지 처리한 뒤 DB에는 두 이벤트가 각각 한 행씩 있었다.
