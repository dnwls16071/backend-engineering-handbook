# Implementing the Point Cancel API

Point Cancel은 보류 중인 포인트만 가용 잔액으로 돌린다. 앞서 커밋한 사용 원장을 취소하는 환불은 별도의 업무 명령이다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 1. 분기 상태별로 잔액을 변경할지 결정한다

TRIED이면 held에서 available로 이동시킨 뒤 CANCELED로 커밋한다. 아직 분기가 없거나 REJECTED면 보류할 잔액이 없으므로 취소 상태만 기록한다. CANCELED 중복 호출은 잔액을 다시 변경하지 않는다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

## 2. 잔액 이력은 원본과 연결한다

CONFIRMED를 받은 조정자가 사용을 되돌려야 한다면 원본 분기와 연결된 별도 포인트 반환을 기록한다. 같은 차감에 대한 반환이 중복되지 않도록 고유 작업 키로 추적한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
