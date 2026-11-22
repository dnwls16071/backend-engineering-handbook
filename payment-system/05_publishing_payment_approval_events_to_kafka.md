# Publishing Payment Approval Events to Kafka

결제 서버가 승인 사실을 저장하면 Wallet과 Ledger가 각각 후속 작업을 시작할 수 있다. 승인 응답 처리와 Kafka 발행 사이의 중단을 복구할 수 있도록 발행 대상은 승인과 함께 DB에 기록한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 1. Confluent Cloud에 테스트 클라이언트를 연결한다

테스트 토픽을 준비하고 대상 Kafka 클러스터의 bootstrap 주소, 접속 권한이 있는 API 키를 사용한다. Java 클라이언트의 SASL/PLAIN 예에서는 SASL_SSL로 TLS 연결을 설정한다. 키와 시크릿은 비밀 저장소나 환경에서 넣고 설정 예시에는 속성 이름만 남긴다. [Confluent Cloud Java 클라이언트](https://docs.confluent.io/cloud/current/cp-component/clients-cloud-config.html)

```properties
bootstrap.servers=<cluster-bootstrap-endpoint>
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
# sasl.jaas.config: load the API key and secret from the runtime secret store
acks=all
enable.idempotence=true
```

## 2. 승인과 이벤트를 한 로컬 트랜잭션에서 저장한다

승인을 반영하는 트랜잭션에서 confirmed_payment와 Outbox 행을 함께 저장한다. 한 주문의 다른 승인이나 같은 결제 시도의 재처리를 확인하고, 새로 확정한 승인에만 새 이벤트를 만든다. event_id는 Relay의 재발행에도 바뀌지 않는다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [PostgreSQL 18 제약](https://www.postgresql.org/docs/18/ddl-constraints.html)

| 이벤트 필드 | 용도 | 근거 |
| --- | --- | --- |
| event_id, event_type, schema_version | 발행 건을 식별하고 소비자가 계약 버전을 구분하는 예시 필드다. | [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| payment_id, order_id, seller_id | 결제와 대상 지갑을 연결한다. 결제 단위 순서가 필요하면 payment_id를 레코드 키로 사용한다. | [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Kafka 4.3 파티션](https://kafka.apache.org/43/getting-started/introduction/) |
| amount, currency, approved_at | 승인 시점의 금액과 통화 및 PG 확인 시각을 전달한다. 소비자에게 필요 없는 PG 응답 원문은 이벤트에서 제외한다. | [토스페이먼츠 Payment 객체](https://docs.tosspayments.com/reference) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |

## 3. 발행 확인 뒤 Outbox 상태를 갱신한다

Relay는 커밋된 미발행 행을 선점하고 DB 잠금 밖에서 Kafka에 전송한다. 발행 성공 응답을 받은 뒤 발행 시각을 남긴다. 발행 성공과 DB 표시 사이에 프로세스가 중단되면 동일 event_id가 다시 전달될 수 있으므로 각 소비자가 중복을 검증한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)

같은 결제의 이벤트 순서가 중요하면 Outbox에 발생 순번을 저장하고, Relay에서 같은 결제의 순번을 건너뛰지 않도록 구성한다. Kafka에서 같은 키로 같은 파티션에 보내도 이미 뒤바뀐 발행 순서는 되돌아오지 않는다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Kafka 4.3 파티션](https://kafka.apache.org/43/getting-started/introduction/)

## 4. 프로듀서 확인과 소비자 중복 방지의 범위를 구분한다

acks=all은 동기화 복제본(ISR)의 확인을 기다린다. min.insync.replicas는 해당 확인을 받을 수 있는 최소 ISR 수를 제한하는 브로커·토픽 설정이다. 실제 설정은 토픽 복제 수와 관리형 서비스가 허용하는 옵션을 함께 확인한다. [Kafka 4.3 프로듀서 설정](https://kafka.apache.org/43/configuration/producer-configs/) · [Kafka 4.3 토픽 설정](https://kafka.apache.org/43/configuration/topic-configs/)

enable.idempotence는 프로듀서 내부 재시도의 중복 기록을 줄인다. Relay가 새 send로 같은 업무 이벤트를 발행하는 경우에는 소비자가 event_id와 업무 키로 중복 변경을 막아야 한다. 송신 확인을 기다리는 전체 시간은 delivery.timeout.ms와 함께 관리한다. [Kafka 4.3 프로듀서 설정](https://kafka.apache.org/43/configuration/producer-configs/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

발행 지연은 미발행 최장 체류 시간으로 보고, 소비 지연은 그룹별 처리량과 함께 본다. 브로커 ACK 직후 Relay 중단을 주입하고, 다시 발행된 이벤트가 지갑·원장에 한 번만 반영되는지 검사한다. [Kafka 4.3 컨슈머 설정](https://kafka.apache.org/43/configuration/consumer-configs/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
