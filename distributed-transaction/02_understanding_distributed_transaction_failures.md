# Understanding Distributed Transaction Failures

주문 DB의 커밋과 재고 서비스의 커밋은 서로 다른 장애 경계를 갖는다. 요청과 응답 사이에도 장애가 발생할 수 있다. [Gray·Lamport · Consensus on Transaction Commit](https://arxiv.org/pdf/cs/0408036) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

## 1. 부분 성공과 응답 유실을 구별한다

| 시점 | 알 수 있는 것 | 필요한 기록 | 근거 |
| --- | --- | --- | --- |
| 주문만 커밋 후 종료 | 주문은 남고 재고 작업은 아직 시작되지 않았을 수 있다. | 주문 상태와 재개할 작업 | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| 재고 커밋 후 응답 유실 | 호출자는 재고 변경 여부를 판단할 수 없다. | 참가자의 멱등 작업 키와 결과 | [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |
| 예약 후 후속 서비스 거절 | 이미 적용된 재고 변경이 남는다. | 보상 대상과 보상 완료 기록 | [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) |

## 2. 호출 중 유지하는 로컬 잠금의 범위를 검토한다

한 서비스가 DB 트랜잭션을 열고 원격 응답을 기다리면 로컬 잠금과 연결 사용 시간이 늘어난다. 요청 처리의 외부 호출과 로컬 기록 경계를 분리하고, 재기동 후 다음 동작을 판단할 수 있게 저장한다. [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
