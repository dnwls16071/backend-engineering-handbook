# Implementing Saga Point Compensation

포인트 보상은 적용된 차감 원장을 참조해 포인트를 돌려주는 별도 로컬 변경이다. 원본과 반환을 함께 읽어 언제 무슨 일이 있었는지 확인할 수 있다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 반환 원장과 잔액을 같이 갱신한다

원본 차감 작업을 잠그고 아직 반환되지 않았으면 원본 금액만큼 계정에 더한다. 원본 차감 키와 반환 종류의 조합에 유니크 제약을 걸고 원장·잔액을 함께 커밋한다. 중복 여부가 불명확하면 저장된 반환 기록을 조회한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 2. 미확인 차감과 반환 실패는 추적 가능하게 둔다

차감이 실제로 없는 것으로 확인되면 반환을 건너뛸 수 있다. 지연된 차감이 가능하면 취소 표시나 명령 순서로 차후 실행을 통제한다. 반환이 실패하면 완료 대신 보상 진행 상태를 남긴다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
