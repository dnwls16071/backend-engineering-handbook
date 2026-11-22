# Reasoning About Kafka Delivery Guarantees

전송 보장은 Kafka에 기록되는 시점, 소비 오프셋의 커밋 시점, 외부 저장소에 업무 효과가 반영되는 시점을 구분해서 판단한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)

## 1. 처리와 커밋 사이에서 유실과 중복을 비교한다

| 전략 | 실패 시 볼 수 있는 결과 | 근거 |
| --- | --- | --- |
| 처리 전에 오프셋 커밋 | 프로세스 종료 시 뒤이어 실행할 업무 효과가 유실될 수 있다. | [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) |
| 처리 후 오프셋 커밋 | 업무 효과 후 커밋 전 장애라면 같은 레코드가 다시 전달될 수 있다. | [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) |
| Kafka 트랜잭션 | Kafka 출력과 소비 오프셋을 함께 반영할 수 있다. read_committed는 중단된 트랜잭션 레코드를 제외한다. 비트랜잭션 레코드도 읽을 수 있다. | [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) |

## 2. Temporal 및 외부 DB의 업무 효과를 구분한다

Kafka 트랜잭션은 원격 Workflow 시작과 Activity의 MySQL 쓰기를 동시에 커밋하는 트랜잭션이 아니다. 시작 요청은 동일 Workflow ID로 재전송하고 최종 쓰기는 이벤트 키의 유니크 제약 등을 사용한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [Temporal · Activities](https://docs.temporal.io/activities) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)
