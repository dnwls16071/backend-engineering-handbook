# Designing an Orchestrated Order Workflow

조정자는 현재 단계와 참가자 결과를 저장하고, 다음 명령 또는 보상 명령을 결정한다. 참가자는 자체 DB와 업무 검증을 소유한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 명령과 결과에 이름을 붙인다

예를 들어 DeductStock 명령의 결과를 APPLIED, REJECTED, UNKNOWN으로 분류한다. APPLIED이면 포인트 차감으로 진행하고, REJECTED이면 그 시점까지 완료된 변경만 보상한다. UNKNOWN이면 참가자 조회나 같은 키 재시도로 판별한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 2. 진행 기록을 실패 뒤 다시 읽는다

현재 단계, 요청 키와 내용, 확인 결과를 저장한다. 명령을 보낸 워커가 죽더라도 다른 워커는 같은 키를 읽고 결과를 확인한다. 단계 갱신의 버전 조건은 참가자 멱등성을 보완한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)
