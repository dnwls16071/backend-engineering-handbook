# Evolving MySQL CDC Schemas and Routing Topics

Debezium은 MySQL의 DDL을 binlog 순서대로 적용해 변경 시점의 행 구조로 레코드를 만든다. Kafka 토픽에 이미 기록된 레코드는 당시 스키마를 유지한다. JDBC Sink의 대상 컬럼을 바꿀 때는 새 레코드와 재처리할 예전 레코드를 모두 고려한다. [MySQL CDC 실습](33_capturing_mysql_binlog_changes_with_debezium.md) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Confluent · JDBC Sink Overview](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

## 1. RegexRouter로 레코드의 토픽 이름을 바꾼다

`RegexRouter`는 레코드의 토픽 이름을 정규식으로 매칭하고 치환 문자열을 적용한다. 소스 커넥터에 다음을 추가하면 앞으로 발행되는 `shop.orders` 변경은 `orders.cdc.v1`에 기록된다. 기존 `mysql-cdc.shop.orders`의 레코드와 소스 오프셋은 그대로 보관되므로 새 토픽으로 과거 데이터도 옮기려면 별도 백필이 필요하다. [Apache Kafka · RegexRouter](https://kafka.apache.org/43/kafka-connect/user-guide/#org.apache.kafka.connect.transforms.RegexRouter)

```properties
transforms=route
transforms.route.type=org.apache.kafka.connect.transforms.RegexRouter
transforms.route.regex=^mysql-cdc[.]shop[.]orders$
transforms.route.replacement=orders.cdc.v1
```

Kafka 원본 토픽을 유지하면서 싱크의 테이블 이름을 정할 수도 있다. 싱크는 `topics`에 지정된 원본 토픽을 구독한 뒤 `unwrap`, `route` 순서로 적용한다. Confluent JDBC Sink가 받는 토픽 이름은 `orders_replica`가 되며, `table.name.format=${topic}`이 이 이름을 대상 테이블로 사용한다. 대상 DB와 연결의 기본 스키마에 그 테이블을 준비한다. 구독과 Kafka 소비 오프셋은 원본 토픽을 기준으로 한다. 37번처럼 테이블 하나를 고정할 때는 `table.name.format=public.orders_replica`로 직접 지정할 수 있다. [Apache Kafka · SinkTask](https://kafka.apache.org/43/javadoc/org/apache/kafka/connect/sink/SinkTask.html) · [Confluent · JDBC Sink Table Mapping](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html) · [MySQL에서 PostgreSQL로 복제](37_replicating_mysql_changes_to_postgresql_with_kafka_connect.md)

```properties
topics=mysql-cdc.shop.orders
transforms=unwrap,route
transforms.unwrap.type=io.debezium.transforms.ExtractNewRecordState
transforms.unwrap.delete.tombstone.handling.mode=tombstone
transforms.route.type=org.apache.kafka.connect.transforms.RegexRouter
transforms.route.regex=^mysql-cdc[.]shop[.](orders)$
transforms.route.replacement=$1_replica
table.name.format=${topic}
```

## 2. 컬럼 변경과 대상을 함께 배포한다

| MySQL 변경 | 레코드와 JDBC Sink에서 확인할 점 |
| --- | --- |
| nullable 컬럼 추가 | 새 레코드에 optional 필드가 추가된다. 과거 레코드에는 필드 자체가 없다. 대상도 `NULL`을 허용하거나 기본값을 둘 수 있다. |
| 기본값이 있는 컬럼 추가 | MySQL의 INSERT 기본값과 Connect 스키마에 표현된 기본값을 각각 확인한다. DB의 기본값은 일반적으로 SQL에 컬럼이 생략됐을 때 적용된다. 대상에 `NULL`을 명시적으로 기록하는 경우에는 싱크의 `replace.null.with.default` 설정도 확인한다. |
| `NOT NULL` 컬럼 추가 | 기존 행과 재생할 레코드에 넣을 값이 필요하다. 먼저 nullable로 추가해 애플리케이션 쓰기를 전환하고 기존 행을 백필한 뒤, 값이 채워졌는지 검사하고 `NOT NULL`을 적용한다. 이전 레코드를 읽는 대상에는 호환 기본값이나 변환을 둔다. |
| `VARCHAR` 길이 변경 | Connect에서는 계속 `STRING`일 수 있다. MySQL 길이와 같은 제약이 필요하면 대상 DDL에 명시한다. 줄이기 전 두 DB에서 `CHAR_LENGTH()`로 한도를 넘는 행을 검사하고, `@@SESSION.sql_mode`에 따른 잘림과 오류를 확인한다. 넓힐 때는 긴 값이 도착하기 전에 대상 한도를 넓힌다. |
| 컬럼 이름 변경·삭제 | 기존 필드와 새 필드를 동시에 수용할 기간을 둔다. 이름 변경은 새 컬럼 추가, 두 컬럼에 쓰기, 백필, 소비자 전환, 이전 컬럼 제거 순서로 진행할 수 있다. 대상에서 먼저 삭제하면 예전 레코드를 재처리할 때 쓰기가 실패할 수 있다. |
| 타입 변경 | 레코드의 Connect 타입과 목적지 JDBC 바인딩을 확인한다. 범위·스케일이 맞지 않거나 형식이 바뀌면 새 컬럼에 변환해서 백필한 뒤 읽기·쓰기를 전환한다. 기본 키 타입 변경은 Kafka의 키 직렬화와 파티션에도 영향을 주므로 새 토픽이나 명시적인 키 마이그레이션이 필요할 수 있다. |

Confluent JDBC Sink의 `auto.evolve=true`는 optional이거나 기본값이 있는 필드가 새로 나타날 때 대상 컬럼을 추가할 수 있다. 타입 변경, 삭제, 제약 마이그레이션은 대상에서 수행한다. 37번처럼 `auto.create=false`, `auto.evolve=false` 설정에서는 새 레코드가 도착하기 전에 대상 DDL을 적용한다. [MySQL 8.4 · ALTER TABLE](https://dev.mysql.com/doc/refman/8.4/en/alter-table.html) · [MySQL 8.4 · SQL Modes](https://dev.mysql.com/doc/refman/8.4/en/sql-mode.html) · [Confluent · Auto-creation and Auto-evolution](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html#auto-creation-and-auto-evolution) · [Confluent · JdbcSinkConfig](https://github.com/confluentinc/kafka-connect-jdbc/blob/master/src/main/java/io/confluent/connect/jdbc/sink/JdbcSinkConfig.java)

## 3. 스키마가 바뀐 위치에서 레코드를 검증한다

33번 실습을 마친 뒤 `shop.orders`에 nullable 메모와 기본값이 있는 채널을 추가한다. 37번의 싱크를 이미 붙였다면 `PUT /connectors/shop-orders-pg-sink/stop`을 요청하고 `STOPPED`를 확인한 뒤 PostgreSQL의 `public.orders_replica`에 아래 컬럼을 먼저 추가한다. 대상 테이블 메타데이터는 싱크 작업을 재개할 때 다시 읽는다. 37번을 기본 스키마부터 시작하려면 33번의 새 실습 환경에서 진행한다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [Confluent · JDBC Sink Table Definition Cache](https://github.com/confluentinc/kafka-connect-jdbc/blob/master/src/main/java/io/confluent/connect/jdbc/sink/DbStructure.java)

```sql
ALTER TABLE public.orders_replica
    ADD COLUMN customer_note VARCHAR(64),
    ADD COLUMN channel VARCHAR(16) NOT NULL DEFAULT 'web';
```

기존 변경이 Kafka에 도착한 뒤 다른 `shop.orders` 쓰기가 없는 실습에서 현재 파티션 끝 오프셋을 읽고 DDL과 UPDATE를 실행한다. DDL 이벤트는 `mysql-cdc`에, UPDATE는 `mysql-cdc.shop.orders`에 기록된다. 컬럼을 추가한 뒤 기존 행의 값을 Kafka에 반영하려면 행 변경을 일으키거나 증분 스냅샷으로 읽는다. [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Apache Kafka · GetOffsetShell](https://github.com/apache/kafka/blob/trunk/tools/src/main/java/org/apache/kafka/tools/GetOffsetShell.java)

```bash
orders_offset=$(mysql_cdc_compose exec -T kafka /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server kafka:29092 --topic mysql-cdc.shop.orders --time -1 |
  awk -F: '$2 == 0 { print $3 }')

mysql_cdc_sql shop <<'SQL'
ALTER TABLE orders ADD COLUMN customer_note VARCHAR(64) NULL;
ALTER TABLE orders ADD COLUMN channel VARCHAR(16) NOT NULL DEFAULT 'web';
UPDATE orders SET customer_note = 'gift' WHERE id = 1;
SQL

mysql_cdc_compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic mysql-cdc.shop.orders \
  --partition 0 --offset "$orders_offset" --max-messages 1 --timeout-ms 30000 |
  jq -e '.payload.op == "u" and .payload.after.id == 1
    and .payload.after.customer_note == "gift" and .payload.after.channel == "web"
    and any(.schema.fields[] | select(.field == "after") | .fields[];
      .field == "customer_note" and .optional)'
```

싱크를 중지했다면 `PUT /connectors/shop-orders-pg-sink/resume`으로 재개한다. 새 레코드를 처리한 뒤 PostgreSQL에서도 `SELECT customer_note, channel FROM public.orders_replica WHERE id = 1`이 `gift`, `web`을 반환하는지 확인한다. 재처리를 검증할 때는 새 두 필드가 없는 스냅샷 레코드와 새 스키마의 UPDATE를 순서대로 처리해 최종 상태를 비교한다.

## 4. `no_data`로 기존 행 없는 첫 실행을 재현한다

Debezium 3.7에서는 예전 설정의 `schema_only`에 해당하는 모드로 `snapshot.mode=no_data`를 사용한다. 새 소스는 테이블 구조와 시작 위치를 읽고, 행 이벤트 발행을 그 위치 이후의 binlog 변경부터 시작한다. 기존 오프셋이 있는 커넥터에 모드만 바꿔 적용하면 이어 읽는 동작과 새 시작을 구분하기 어렵다. 새 커넥터 이름과 `topic.prefix`, 전용 스키마 이력 토픽을 사용하면 같은 Connect 워커에서도 각 실행의 소스 오프셋과 출력이 독립적으로 기록된다. 동시에 붙는 MySQL 복제 클라이언트에는 서로 다른 `database.server.id`를 지정한다. [Debezium · MySQL Snapshot Settings](https://debezium.io/documentation/reference/3.7/connectors/mysql.html#mysql-snapshots)

```bash
mysql_cdc_compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --create --if-not-exists \
  --topic mysql-cdc-r2-schema-history --partitions 1 --replication-factor 1 \
  --config cleanup.policy=delete --config retention.ms=-1 --config retention.bytes=-1

jq '. + {
  "database.server.id": "184055",
  "topic.prefix": "mysql-cdc-r2",
  "snapshot.mode": "no_data",
  "schema.history.internal.kafka.topic": "mysql-cdc-r2-schema-history"
}' shop-mysql-source.json |
  curl -fsS -X PUT -H 'Content-Type: application/json' \
    "$connect_url/connectors/shop-mysql-source-r2/config" --data-binary @-

curl -fsS "$connect_url/connectors/shop-mysql-source-r2/status" | jq '{connector, tasks}'
```

`shop-mysql-source-r2`의 작업이 `RUNNING`이고 Connect 로그에 초기 스냅샷 완료와 스트리밍 시작이 표시된 뒤, 아래 INSERT를 실행한다. 첫 레코드로 새 행의 `op=c`를 확인한다. 반복할 때는 커넥터 이름, `topic.prefix`, 스키마 이력 토픽과 테스트 행의 키를 새로 정한다. 별도 분산 워커를 띄울 경우 `group.id`와 세 내부 토픽도 고유하게 지정한다. [Apache Kafka · Distributed Workers](https://kafka.apache.org/43/kafka-connect/user-guide/) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html)

```bash
mysql_cdc_sql shop -e "INSERT INTO orders (id, status, amount) VALUES (3501, 'created', 3.50)"
mysql_cdc_read 1 mysql-cdc-r2.shop.orders | cut -f2- |
  jq -e '.payload.op == "c" and .payload.after.id == 3501'
```
