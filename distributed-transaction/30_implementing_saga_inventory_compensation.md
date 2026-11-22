# Implementing Saga Inventory Compensation

재고 복원 API는 원본 차감의 작업 키를 사용한다. 복원량을 원본에서 읽고 복원한 사실을 원본과 함께 추적한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 복원 범위를 원본 작업으로 제한한다

원본 작업을 잠근 뒤 APPLIED이고 복원하지 않았으면 해당 상품에 성공 차감량을 더한다. 원본당 하나의 복원 기록과 재고 증가를 같은 트랜잭션에 넣는다. 중복 복원은 기존 결과를 반환한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)

## 2. 복원보다 늦게 올 수 있는 차감 요청을 처리한다

원본이 없으면 먼저 조정 기록으로 늦은 실행 가능성을 확인한다. 미적용을 종료 처리하려면 참가자가 같은 작업 키의 뒤늦은 차감을 거부하는 취소 표시를 저장하거나 그에 상응하는 실행 순서를 보장해야 한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)
