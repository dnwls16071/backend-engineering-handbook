# Building Reliable CDC Pipelines with Debezium

Debezium의 PostgreSQL 소스 커넥터는 데이터베이스의 초기 상태를 스냅샷으로 읽고, 커밋된 변경을 WAL(Write-Ahead Log)에서 디코딩해 Kafka로 보낸다. `snapshot.mode=initial`은 저장된 위치가 없는 첫 실행에서 스냅샷을 수행하고, 이후에는 스냅샷 기준 위치부터 이어서 변경을 읽는다. 재시작 시에는 Kafka Connect가 저장한 LSN(Log Sequence Number)에서 재개한다. [Debezium · PostgreSQL Connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html)

## 1. 재시작에 필요한 상태

- **Publication과 복제 슬롯**을 따로 관리한다. Publication은 발행할 테이블을 지정한다. 논리 복제 슬롯은 소비 진행 위치를 관리하고 필요한 WAL이 보존되도록 한다. 중지 후 재개하려면 같은 슬롯과 Connect 오프셋을 유지한다. [Debezium · PostgreSQL Connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html) · [PostgreSQL · Logical Decoding](https://www.postgresql.org/docs/17/logicaldecoding-explanation.html)
- **복구 중 중복**을 처리한다. Kafka에 쓰고 소스 오프셋을 저장하기 전에 장애가 나면 이미 발행한 변경이 다시 전달될 수 있다. 상태를 복제하는 소비자는 기본 키 기준으로 upsert와 삭제를 멱등하게 처리하고, 부수 효과를 실행하는 소비자는 이벤트 식별자로 중복을 막는다. [Debezium · Behavior When Things Go Wrong](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-when-things-go-wrong)
- **지연과 WAL 보관량**을 함께 본다. Connect REST에서 커넥터와 작업 상태를 확인하고, `pg_replication_slots`에서 슬롯의 `active`, `restart_lsn`, `confirmed_flush_lsn`을 본다. 슬롯이 장기간 뒤처지면 WAL이 누적된다. 재개에 필요한 WAL이 사라졌다면 남은 로그 범위를 확인하고 스냅샷과 대상 상태 재동기화 계획을 세운다. [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api) · [PostgreSQL · pg_replication_slots](https://www.postgresql.org/docs/17/view-pg-replication-slots.html) · [Debezium · Recovery](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-when-things-go-wrong)

## 2. 로컬 커넥터 등록

01번 실습의 `compose.yaml`과 같은 디렉터리에 `compose.cdc.yaml`을 저장한다. PostgreSQL은 `wal_level=logical`로 시작한다. 아래 계정은 로컬 실습용이며 운영에서는 복제 권한과 대상 테이블 조회 권한을 부여한 전용 계정을 사용한다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기) · [Debezium · PostgreSQL Connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html) · [Debezium · Kafka Connect Tutorial](https://debezium.io/documentation/reference/stable/kc-tutorial.html)

```yaml
services:
  postgres:
    image: postgres:17-alpine
    command: ["postgres", "-c", "wal_level=logical"]
    environment:
      POSTGRES_DB: cdc
      POSTGRES_USER: cdc
      POSTGRES_PASSWORD: local-cdc-password
    healthcheck:
      test: ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "cdc", "-d", "cdc"]
      interval: 2s
      timeout: 3s
      retries: 30
  debezium:
    image: quay.io/debezium/connect:3.7
    depends_on:
      kafka: { condition: service_healthy }
      postgres: { condition: service_healthy }
    ports: ["127.0.0.1:18084:8083"]
    environment:
      BOOTSTRAP_SERVERS: kafka:29092
      GROUP_ID: cdc-connect
      CONFIG_STORAGE_TOPIC: cdc-connect-configs
      OFFSET_STORAGE_TOPIC: cdc-connect-offsets
      STATUS_STORAGE_TOPIC: cdc-connect-status
      CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR: "1"
      CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR: "1"
      CONNECT_STATUS_STORAGE_REPLICATION_FACTOR: "1"
```

새 실습 환경에서 테이블과 publication을 만들고 `PUT /connectors/{name}/config`로 커넥터를 등록한다. 같은 이름으로 다시 요청하면 설정을 갱신한다. `pgoutput`은 PostgreSQL의 내장 플러그인이다. `topic.prefix`, 스키마 이름, 테이블 이름이 출력 토픽 `cdc-demo.public.orders`를 이룬다. [Debezium · PostgreSQL Connector Properties](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-connector-properties) · [Debezium · Container Entry Point](https://github.com/debezium/container-images/blob/main/connect-base/3.7/docker-entrypoint.sh) · [Apache Kafka · Connect REST API](https://kafka.apache.org/43/kafka-connect/user-guide/#rest-api)

```bash
cdc_compose() { docker compose -f compose.yaml -f compose.cdc.yaml "$@"; }
cdc_sql() { cdc_compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U cdc -d cdc; }
cdc_compose up -d --wait
cdc_sql <<'SQL'
CREATE TABLE public.orders (id integer PRIMARY KEY, status text NOT NULL);
ALTER TABLE public.orders REPLICA IDENTITY FULL;
CREATE PUBLICATION cdc_orders_pub FOR TABLE public.orders;
INSERT INTO public.orders VALUES (1, 'existing');
SQL

connect=http://127.0.0.1:18084
curl -fsS --retry 30 --retry-all-errors --retry-delay 1 "$connect/connector-plugins" |
  jq -e 'any(.[]; .class == "io.debezium.connector.postgresql.PostgresConnector")'
curl -fsS -X PUT -H 'Content-Type: application/json' \
  "$connect/connectors/orders-cdc/config" -d @- <<'JSON'
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "tasks.max": "1",
  "database.hostname": "postgres", "database.port": "5432",
  "database.user": "cdc", "database.password": "local-cdc-password", "database.dbname": "cdc",
  "plugin.name": "pgoutput", "slot.name": "cdc_orders_slot", "slot.drop.on.stop": "false",
  "publication.name": "cdc_orders_pub", "publication.autocreate.mode": "disabled",
  "table.include.list": "public[.]orders", "topic.prefix": "cdc-demo",
  "snapshot.mode": "initial", "tombstones.on.delete": "true",
  "topic.creation.default.replication.factor": "1", "topic.creation.default.partitions": "1",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter", "key.converter.schemas.enable": "false",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter", "value.converter.schemas.enable": "false"
}
JSON
curl -fsS "$connect/connectors/orders-cdc/status" | jq '{connector, tasks}'
```

## 3. 스냅샷과 INSERT·UPDATE·DELETE 검증

커넥터와 작업이 모두 `RUNNING`이면 같은 셸에서 실행한다. 새 토픽에서 `op=r`인 스냅샷 레코드를 먼저 확인하고 다른 키로 변경을 일으킨다. `REPLICA IDENTITY FULL`은 UPDATE·DELETE의 `before`에서 이전 상태까지 확인하기 위해 설정했다. 삭제 후에는 같은 키와 Kafka의 `null` 값으로 구성된 tombstone이 이어진다. [Debezium · PostgreSQL Change Event Values](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-change-event-values)

```bash
(
  set -euo pipefail
  cdc_read() {
    cdc_compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
      --bootstrap-server kafka:29092 --topic cdc-demo.public.orders --from-beginning \
      --max-messages "$1" --timeout-ms 30000 --formatter-property print.key=true
  }
  cdc_read 1 | cut -f2- | jq -e '.op == "r" and .after.status == "existing"'
  cdc_sql <<'SQL'
INSERT INTO public.orders VALUES (2, 'created');
UPDATE public.orders SET status = 'paid' WHERE id = 2;
DELETE FROM public.orders WHERE id = 2;
SQL
  cdc_read 5 | jq -Rse '
    split("\n") | map(select(length > 0) | split("\t") | map(fromjson))
    | (map(.[1].op) == ["r","c","u","d",null])
      and (.[1:] | map(.[0].id) == [2,2,2,2])
      and (.[1][1].after.status == "created")
      and (.[2][1].before.status == "created" and .[2][1].after.status == "paid")
      and (.[3][1].before.status == "paid" and .[3][1].after == null and .[4][1] == null)'
)
```

재시작 검증에서는 같은 슬롯과 오프셋을 둔 채 워커를 중지하고, 중지 중 새 행을 추가한다. 워커가 다시 실행되면 해당 키의 `op=c`가 도착하고, 동일 이벤트가 다시 전달되어도 대상 상태가 그대로 유지되는지 확인한다. [Debezium · Behavior When Things Go Wrong](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-when-things-go-wrong)
