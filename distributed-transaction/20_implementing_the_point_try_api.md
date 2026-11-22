# Implementing the Point Try API

포인트 Try는 계정의 가용 포인트를 보류 잔액으로 옮긴다. 분기 키는 계정과 정수 단위의 차감량을 묶는다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 한 로컬 트랜잭션에서 보류와 분기 결과를 저장한다

point_branch의 키를 확보한 뒤, 처음 실행이면 아래와 같이 가용량을 검사하며 잔액을 갱신한다. 성공이면 TRIED, 계정이 없거나 부족하면 REJECTED를 저장한다. 기존 분기이면 계정·금액 일치 여부와 상태를 반환한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

```sql
-- point_branch를 잠근 뒤 같은 트랜잭션에서 실행하는 준비 단계의 갱신
UPDATE point_balance
SET available = available - ?, held = held + ?
WHERE account_id = ? AND available >= ?;
```

## 2. 잔액 불변식과 보존 기간을 검증한다

Try 직후 가용 잔액은 줄고 보류 잔액은 같은 양만큼 늘어야 한다. 지연된 Try가 앞선 취소를 뒤집을 수 없도록 분기 상태를 보존한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · CHECK Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html)
