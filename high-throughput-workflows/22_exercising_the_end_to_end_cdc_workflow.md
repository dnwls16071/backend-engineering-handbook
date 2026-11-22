# Exercising the End-to-End CDC Workflow

로컬 개발 서버에서 Temporal을 실행하고, 하나의 주문과 아웃박스 INSERT가 Kafka와 Workflow 이력을 거쳐 처리 결과 한 행으로 이어지는지 확인한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Temporal CLI · Server](https://docs.temporal.io/cli/command-reference/server) · [Temporal · Workflows](https://docs.temporal.io/workflows)

## 1. 로컬 서버와 앱을 실행한다

[인프라 및 커넥터](21_registering_a_mysql_outbox_connector.md)의 스냅샷이 끝난 상태에서 호스트에 설치한 Temporal CLI의 개발 서버를 시작한다. 별도 셸에서 build.gradle.kts와 소스·설정 파일을 둔 프로젝트의 앱을 실행한다. [Temporal CLI · Server](https://docs.temporal.io/cli/command-reference/server) · [Temporal SDK 1.31.0 · WorkerFactory](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/worker/WorkerFactory.java) · [Spring Boot 3.5 · System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html)

```bash
# 셸 1
temporal server start-dev

# 셸 2
WORKFLOW_DB_PASSWORD=local-workflow-app ./gradlew bootRun
```

## 2. 하나의 로컬 트랜잭션으로 주문을 발행한다

아래 주문·이벤트 ID는 실습의 첫 실행용 예시다. 독립 실습을 다시 수행할 때는 주문 ID와 UUID를 새로 선택한다. 같은 ID로 재전달 시험을 할 때만 메시지를 다시 발행한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid)

```bash
docker compose exec -T mysql-source sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" workflow_lab' <<'SQL'
SET @order_id = 'lab-order-01';
SET @event_id = 'c895b567-390b-47bd-9ac0-cde78bf31c15';
START TRANSACTION;
INSERT INTO orders (id, status) VALUES (@order_id, 'ACCEPTED');
INSERT INTO order_outbox (id, aggregatetype, aggregateid, type, payload)
VALUES (@event_id, 'orders', @order_id, 'OrderRequested',
        JSON_OBJECT('eventId', @event_id, 'orderId', @order_id, 'type', 'OrderRequested'));
COMMIT;
SQL

temporal workflow describe --workflow-id order-event-c895b567-390b-47bd-9ac0-cde78bf31c15
docker compose exec -T mysql-source sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" workflow_lab' <<'SQL'
SELECT event_id, order_id, processed_at FROM processed_order_events;
SQL
```

## 3. 재전달과 대기 상태에서 결과를 검증한다

| 시나리오 | 기대 결과 | 근거 |
| --- | --- | --- |
| 정상 실행 | 워크플로우가 완료되고 해당 eventId의 처리 행이 하나 있다. | [Temporal · Workflows](https://docs.temporal.io/workflows) · [Temporal · Activities](https://docs.temporal.io/activities) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) |
| 같은 JSON 레코드 재발행 | 같은 Workflow ID의 실행을 다시 만들지 않고, 처리 행은 여전히 하나다. | [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) |
| Worker가 담당 Task Queue를 잠시 폴링하지 않음 | 정상 접수된 실행이 대기하다가 Worker를 복구하면 이어서 진행한다. 이 사례는 리스너와 Worker를 분리해 구동하거나 폴링만 중단해 재현한다. | [Temporal · Task Queues](https://docs.temporal.io/task-queue) · [Temporal · Workflows](https://docs.temporal.io/workflows) |

정상 완료 후에는 같은 키와 본문의 이벤트를 로컬 Kafka에 한 번 더 보낸다. order-workflow 그룹의 오프셋이 진행된 뒤 Workflow의 Run ID와 DB 처리 행을 다시 확인한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)

```bash
printf '%s\n' 'lab-order-01|{"eventId":"c895b567-390b-47bd-9ac0-cde78bf31c15","orderId":"lab-order-01","type":"OrderRequested"}' |
  docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server kafka:29092 --topic workflow.orders \
    --property parse.key=true --property 'key.separator=|'
docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:29092 --group order-workflow --describe
```

DB 조회나 CLI 조회는 기한 내에 반복해 비동기 완료를 확인한다. 멈추면 MySQL 아웃박스, Kafka 레코드, Workflow 이력, 처리 테이블을 순서대로 확인한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal CLI · Workflow](https://docs.temporal.io/cli/command-reference/workflow)
