# Implementing Saga Point Deduction

포인트 차감 서비스는 operationId와 계정, 정수 포인트 금액으로 차감을 식별한다. 계정 잔액과 원장의 변경을 한 로컬 커밋으로 처리한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 충분한 잔액만 차감되게 한다

원본 작업 키의 중복을 확인한 뒤 가용 잔액이 충분한 행만 조건부 갱신한다. 성공하면 차감 원장과 APPLIED 결과를 함께 저장하고, 부족하면 업무 거절 결과를 기록해 조정자가 보상 분기를 선택할 수 있게 한다. [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 2. 원장과 잔액이 함께 복구되는지 확인한다

잔액 갱신 뒤 원장 기록이 실패하면 로컬 트랜잭션을 롤백한다. 커밋 응답 유실 뒤 같은 operationId를 다시 보내도 한 건의 차감 원장만 있어야 한다. [MySQL 8.4 · InnoDB Error Handling](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
