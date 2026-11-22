# Implementing Saga Inventory Deduction

재고 차감 API는 operationId, 상품, 수량을 받는다. 직접 차감한 로컬 결과와 작업 기록을 함께 커밋한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)

## 1. 중복과 가용량 경쟁을 같은 경계에서 처리한다

작업 키를 확보하고 요청 내용이 일치하는지 검사한다. 첫 시도는 조건부 UPDATE로 가용 재고를 줄이고 APPLIED 또는 REJECTED를 저장한다. 같은 키의 재요청은 저장된 결과를 돌려준다. [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

```sql
-- operationId를 확보하고 잠근 로컬 트랜잭션 안에서 실행
UPDATE stock SET available = available - ?
WHERE product_id = ? AND available >= ?;
```

## 2. 보상이 사용할 근거를 기록한다

정방향 APPLIED 작업에 상품과 실제 차감량을 보관한다. 보상 API는 호출자 입력의 임의 수량 대신 이 기록을 사용한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
