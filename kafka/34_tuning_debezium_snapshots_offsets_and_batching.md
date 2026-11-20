# Tuning Debezium Snapshots, Offsets, and Batching

MySQL CDC의 초기 스냅샷은 기존 행을 Kafka에 채운다. 이후 재시작의 복구 범위는 Connect가 저장한 소스 오프셋과 MySQL에 남아 있는 binlog가 결정한다. 처리량을 조정할 때는 Debezium의 소스 큐와 JDBC Sink의 DB 기록 배치를 각각 측정한다. [MySQL CDC 실습](33_capturing_mysql_binlog_changes_with_debezium.md) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Confluent · JDBC Sink Configuration](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)

## 1. 스냅샷에서 스트리밍으로 전환한다

`snapshot.mode=initial`은 저장된 오프셋이 없으면 일관된 읽기 시점의 binlog 위치와 테이블 구조를 확보하고 기존 행을 `op=r`로 발행한다. 스냅샷 완료를 기록한 뒤 그 위치부터 binlog를 읽는다. 초기 스냅샷 도중 장애가 나면 다시 시작할 때 스냅샷을 처음부터 수행할 수 있다. 큰 테이블을 읽기 전에 원본 DB의 I/O와 긴 트랜잭션 비용을 측정한다. `min.row.count.to.stream.results`는 스냅샷 조회 결과를 메모리에 쌓는 대신 스트리밍할 행 수 기준이며, `0`으로 지정하면 모든 결과를 스트리밍한다. 나중에 특정 테이블의 기존 행을 보충하려면 스트리밍 중 기본 키 범위를 청크로 읽는 증분 스냅샷을 검토한다. [Debezium · MySQL Snapshots](https://debezium.io/documentation/reference/3.7/connectors/mysql.html#mysql-snapshots)

| 위치 | 의미 |
| --- | --- |
| Debezium 소스 오프셋 | MySQL binlog 파일·바이트 위치와 재개에 필요한 이벤트·행 위치를 저장한다. GTID를 켠 환경에서는 처리한 GTID 집합도 기록한다. 33번 분산 워커에서는 `mysql-cdc-connect-offsets`에 보관한다. |
| Debezium 스키마 이력 | 이전 binlog를 그 시점의 스키마로 해석하도록 DDL 이력을 저장한다. 실습에서는 `mysql-cdc-schema-history`에 보관한다. |
| JDBC Sink 소비 오프셋 | 싱크가 Kafka 토픽의 어느 파티션에서 얼마나 읽었는지 기록한다. Connect REST의 싱크 오프셋에서 확인한다. |

Kafka 발행 후 소스 오프셋이 저장되기 전에 장애가 나면 일부 변경이 재발행될 수 있다. 싱크에서도 DB 커밋 뒤 Kafka 소비 위치를 기록하기 전 장애가 나면 같은 이벤트를 다시 받을 수 있다. `id`가 안정적인 행 상태 복제는 기본 키 upsert와 삭제로 이 재처리를 흡수한다. [Debezium · MySQL Failure Handling](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [Confluent · JDBC Sink Overview](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/overview.html)

## 2. 저장된 위치와 binlog 보존 범위를 비교한다

33번 실습에서 다섯 레코드를 확인한 뒤 같은 셸에서 커넥터를 중지한다. `status`가 `STOPPED`를 표시하면 REST 오프셋의 `offset.file`을 `SHOW BINARY LOGS`에 나온 파일 목록과 대조한다. `SHOW BINARY LOG STATUS`는 서버가 현재 쓰는 위치를 보여 준다. 소스 오프셋이 존재하는지 확인하고 중단 중에 발생한 변경이 다음 절에서 재개되는지 본다. [MySQL 8.4 · SHOW BINARY LOGS](https://dev.mysql.com/doc/refman/8.4/en/show-binary-logs.html) · [MySQL 8.4 · SHOW BINARY LOG STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-binary-log-status.html) · [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)

```bash
source_api="$connect_url/connectors/shop-mysql-source"
curl -fsS -X PUT "$source_api/stop"
curl -fsS "$source_api/status" | jq '.connector.state'
```

```bash
curl -fsS "$source_api/offsets" | jq '.offsets'
mysql_cdc_sql -e 'SHOW BINARY LOGS; SHOW BINARY LOG STATUS; SELECT @@GLOBAL.binlog_expire_logs_seconds;'
```

- **필요한 로그가 남아 있을 때**는 기존 커넥터 이름, `topic.prefix`, 오프셋 및 스키마 이력을 유지하고 재개한다. 장애 조치로 다른 MySQL 서버에 연결할 때는 이어 읽을 트랜잭션을 새 서버가 보존하는지 확인한다. GTID를 사용하면 서버 간 같은 트랜잭션을 식별할 수 있다.
- **필요한 로그가 만료됐을 때**는 `initial` 모드에서 재개가 실패한다. `when_needed`로 설정하면 필요한 위치를 찾지 못했을 때 다시 스냅샷을 수행할 수 있다. 재스냅샷으로 현재 행은 다시 채울 수 있다. 사라진 업데이트 이력이나 삭제 이벤트는 백업·아카이브로 복구하거나, 대상 테이블을 새로 채워 현재 원본과 대조한다. 기존 대상에 upsert만 하면 로그가 없던 구간에 삭제된 행이 남을 수 있다.
- **이력 토픽이 유실됐을 때**는 오프셋에 대응하는 스키마 이력을 복원한다. `snapshot.mode=recovery`는 현재 테이블 구조로 이력 토픽을 재구축하는 모드다. 마지막 종료 후 DDL이 커밋된 환경에서는 당시 스키마 이력을 가진 백업을 사용하거나 새 기준점에서 재동기화한다.

`binlog_expire_logs_seconds`에는 예상 최대 중단 시간과 재시작 후 밀린 변경을 따라잡을 시간까지 포함한다. 대량 변경일의 binlog 증가량과 디스크 여유로 설정값을 검증한다. [MySQL 8.4 · Binary Logging Options](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html) · [Debezium · MySQL Connector](https://debezium.io/documentation/reference/3.7/connectors/mysql.html)

## 3. 금액과 시간을 원본과 대조한다

`DECIMAL`과 `NUMERIC`은 기본 `decimal.handling.mode=precise`에서 `BigDecimal`을 담는 Connect 논리 타입 `org.apache.kafka.connect.data.Decimal`로 매핑된다. 스키마를 포함한 JSON Converter의 기본 `decimal.format=BASE64`에서는 바이트가 Base64 문자열로 보인다. 스케일은 스키마의 `parameters.scale`에 있다. `decimal.format=NUMERIC`은 JSON 숫자로 표현하지만 소비자의 JSON 파서가 이 값을 `double`로 읽으면 정밀도를 잃을 수 있다. Debezium의 `decimal.handling.mode=double`은 소스 단계부터 근삿값을 사용하고 `string`은 자리수를 유지한 문자열과 함께 문자열 스키마를 보낸다. 금액을 JDBC로 복제할 때는 Decimal 논리 타입과 목적지 `NUMERIC(12,2)`를 사용한다. `BIGINT UNSIGNED`가 `2^63-1`을 넘을 수 있다면 `bigint.unsigned.handling.mode=precise`와 대상 컬럼의 표현 범위를 확인한다. [Debezium · MySQL Data Mappings](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Apache Kafka · JsonConverter Configuration](https://github.com/apache/kafka/blob/trunk/connect/json/src/main/java/org/apache/kafka/connect/json/JsonConverterConfig.java)

중지 중 `id=1`의 금액을 바꾼 뒤 재개한다. 33번부터 순서대로 실행했다면 여섯 번째 레코드의 `op=u`, `amount`의 Decimal 스키마와 바이너리 값을 확인할 수 있다. `BNI=`는 1234를 담은 바이트의 Base64이고 스케일 2를 적용하면 12.34다.

```bash
mysql_cdc_sql shop -e 'UPDATE orders SET amount = 12.34 WHERE id = 1; SELECT id, amount FROM orders WHERE id = 1;'
curl -fsS -X PUT "$source_api/resume"
mysql_cdc_read 6 | tail -n 1 | cut -f2- | jq -e '
  .payload.op == "u" and .payload.after.id == 1 and .payload.after.amount == "BNI="
  and any(.schema.fields[] | select(.field == "after") | .fields[];
    .field == "amount" and .name == "org.apache.kafka.connect.data.Decimal" and .parameters.scale == "2")'
```

MySQL `DATETIME`은 시간대 없는 달력 시각이다. 기본 `time.precision.mode=adaptive_time_microseconds`에서 `DATETIME(3)`까지는 밀리초, `DATETIME(4~6)`은 마이크로초 정수로 옮긴다. 이 정수는 UTC를 기준으로 달력 시각을 인코딩한다. `TIMESTAMP`는 MySQL이 입력 세션의 시간대에서 UTC로 바꿔 저장하며, Debezium은 기본적으로 UTC의 `io.debezium.time.ZonedTimestamp` 문자열로 발행한다. JDBC Sink의 `db.timezone`과 DB 세션 시간대, 컬럼 정밀도를 함께 확인하고 기본 논리 타입 외의 시간 필드는 대상 바인딩을 검증한다. `time.precision.mode=connect`로 바꾸면 `DATETIME`의 마이크로초가 손실될 수 있다. [Debezium · MySQL Temporal Values](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [MySQL 8.4 · DATE, DATETIME, and TIMESTAMP](https://dev.mysql.com/doc/refman/8.4/en/datetime.html) · [Confluent · JDBC Sink Configuration](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html)

## 4. 소스 큐와 JDBC 배치를 따로 조정한다

| 단계 | 설정 | 확인할 점 |
| --- | --- | --- |
| Debezium 배치 | `max.batch.size` 기본값 `2048` | Connect에 넘기는 한 번의 레코드 묶음 상한이다. MySQL 커넥터는 한 작업으로 binlog를 읽는다. |
| Debezium 큐 | `max.queue.size` 기본값 `8192`, `max.queue.size.in.bytes` 기본값 `0` | 레코드 수 한도를 `max.batch.size`보다 크게 잡는다. 바이트 한도도 주면 둘 중 먼저 찬 한도에서 읽기에 역압력이 걸린다. 아직 큐에만 있는 레코드는 저장 오프셋에 포함되지 않는다. |
| JDBC 추가·갱신 | `insert.mode=upsert`, `batch.size` 기본값 `3000` | 테이블별로 JDBC 쓰기를 묶는다. 들어온 레코드 수, 스키마 변경, 테이블 분기 때문에 한도보다 작은 배치가 만들어질 수 있다. |
| JDBC 소비 | 워커의 `consumer.max.poll.records` 또는 싱크의 `consumer.override.max.poll.records` | 한 번의 `poll()` 상한이 JDBC 배치 크기 이상이어야 그 크기에 도달할 수 있다. 커넥터별 설정은 워커의 `connector.client.config.override.policy`가 허용해야 한다. |

싱크에서 `batch.size=500`, `consumer.override.max.poll.records=500`으로 시작해 본다. 대량 upsert에서 DB 커밋 지연과 잠금 대기, Kafka 싱크 소비 지연을 비교한다. DB 작업이 다음 `poll()`까지 `max.poll.interval.ms`를 넘기면 그룹 재조정으로 처리가 반복될 수 있다. 소스는 Debezium의 `QueueRemainingCapacity`, `MilliSecondsBehindSource`와 워커의 힙, Kafka 쓰기 지연을 함께 본다. 소스 큐가 계속 차면 Kafka로 내보내는 속도를 확인하고, 싱크의 소비 지연이 늘면 JDBC 쓰기와 DB 병목을 확인한다. [Debezium · MySQL Connector Metrics](https://debezium.io/documentation/reference/3.7/connectors/mysql.html) · [Confluent · JDBC Sink Configuration](https://docs.confluent.io/kafka-connectors/jdbc/current/sink-connector/sink_config_options.html) · [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · Connect User Guide](https://kafka.apache.org/43/kafka-connect/user-guide/)

37번의 PostgreSQL 싱크를 붙인 실습 환경에서 REST API로 배치와 소비 설정을 적용한다. 싱크 작업이 다시 `RUNNING`이면 새 키 500개를 추가하고 같은 키를 갱신한다. MySQL의 `shop.orders`와 PostgreSQL의 `public.orders_replica`에서 이 범위의 행 개수, `paid` 상태의 행 개수, 금액 합계를 비교한다. [MySQL에서 PostgreSQL로 복제](37_replicating_mysql_changes_to_postgresql_with_kafka_connect.md) · [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [MySQL 8.4 · WITH](https://dev.mysql.com/doc/refman/8.4/en/with.html)

```bash
curl -fsS -X PATCH -H 'Content-Type: application/json' \
  "$connect_url/connectors/shop-orders-pg-sink/config" --data-binary @- <<'JSON'
{
  "batch.size": "500",
  "consumer.override.max.poll.records": "500"
}
JSON
```

```bash
mysql_cdc_sql shop <<'SQL'
INSERT INTO orders (id, status, amount)
WITH RECURSIVE seq(n) AS (
    SELECT 1000
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 1499
)
SELECT n, 'created', 1.25 FROM seq;
UPDATE orders SET status = 'paid' WHERE id BETWEEN 1000 AND 1499;
SQL
```

```sql
SELECT COUNT(*) AS rows_written,
       COUNT(CASE WHEN status = 'paid' THEN 1 END) AS paid_rows,
       SUM(amount) AS total
FROM orders
WHERE id BETWEEN 1000 AND 1499;
```

PostgreSQL에서는 `FROM public.orders_replica`로 바꾼다. 싱크가 처리를 마치면 두 DB의 결과가 `500`, `500`, `625.00`으로 일치해야 한다. 부하 조건을 비교할 때는 새 키 범위로 같은 쓰기를 반복하고 처리량뿐 아니라 지연과 재시작 뒤 최종 상태를 확인한다.
