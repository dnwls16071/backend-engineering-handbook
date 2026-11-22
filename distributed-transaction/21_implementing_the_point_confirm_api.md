# Implementing the Point Confirm API

Point Confirm은 보류 포인트를 확정 차감으로 전환한다. 참가자 분기와 원장은 같은 로컬 트랜잭션에서 갱신한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 보류 잔액과 원장을 함께 변경한다

TRIED 분기를 잠그고 해당 계정의 held를 차감한 뒤 포인트 사용 원장을 추가한다. 원장의 branchId에 유니크 제약을 둔다. CONFIRMED로의 상태 변경까지 함께 커밋하고, 중간 오류면 모두 롤백한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [MySQL 8.4 · InnoDB Error Handling](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)

## 2. 응답 유실 후 확정을 다시 요청한다

이미 CONFIRMED인 분기는 원장 행을 하나 더 만들지 않고 확정 결과를 반환한다. 계정·금액 불일치나 예약 없는 Confirm은 분기 상태와 조정 결정을 대조할 수 있게 오류로 남긴다. [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
