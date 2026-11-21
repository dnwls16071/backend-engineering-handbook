# Locking Reads with NOWAIT and SKIP LOCKED

MySQL 8.4의 InnoDB 잠금 조회는 충돌하는 행 잠금을 기본적으로 기다린다. `NOWAIT`는 충돌 시 즉시 오류 `3572` (`ER_LOCK_NOWAIT`)를 반환하고, `SKIP LOCKED`는 잠긴 행을 결과에서 건너뛴다. 두 옵션은 `FOR UPDATE` 또는 `FOR SHARE` 뒤에 쓰며, `OF`로 잠글 테이블을 지정하면 `OF` 목록 뒤에 쓴다. 잠금 절은 `ORDER BY`와 `LIMIT` 뒤에 온다. [MySQL SELECT 구문](https://dev.mysql.com/doc/refman/8.4/en/select.html) · [MySQL 오류 3572](https://dev.mysql.com/doc/mysql-errors/8.4/en/server-error-reference.html#error_er_lock_nowait)

## 작업 하나를 선점한다

`jobs`는 `job_id`를 기본 키로, `(status, job_id)`를 보조 인덱스로 가진 InnoDB 작업 테이블이다. `EXPLAIN`에서 상태 조건과 정렬에 이 인덱스를 사용하는지 확인한다. 잠금 범위는 실제로 스캔한 인덱스 레코드와 격리 수준의 영향을 받는다. [InnoDB의 문장별 잠금 범위](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)

```sql
START TRANSACTION;

SELECT j.job_id
FROM jobs AS j
WHERE j.status = 'READY'
ORDER BY j.job_id
LIMIT 1
FOR UPDATE OF j SKIP LOCKED;

-- 행이 반환되면 그 job_id를 ?에 바인딩한다.
UPDATE jobs
SET status = 'RUNNING'
WHERE job_id = ? AND status = 'READY';

COMMIT;
```

행이 없으면 갱신 없이 트랜잭션을 끝내고 다음 폴링을 예약한다. 행이 있으면 같은 트랜잭션에서 상태를 바꾼 뒤 커밋하고 실제 작업을 시작한다. `SKIP LOCKED`는 앞의 작업을 건너뛸 수 있어 엄격한 FIFO를 보장하지 않는다. 오래 대기한 작업을 관찰하고, 워커가 장애로 중단되면 `RUNNING` 상태의 만료 기준에 따라 회수한다. 재처리 시 외부 효과의 중복을 막으려면 작업 ID를 멱등성 키로 사용한다. [MySQL 잠금 조회](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

## 경합과 재시도를 처리한다

- `NOWAIT` 오류로 선점을 포기할 때는 롤백으로 트랜잭션을 닫는다. 다시 시도하는 경우 잠시 기다린 뒤 새 트랜잭션에서 후보를 조회한다. 데드락은 InnoDB가 트랜잭션 전체를 롤백하므로 처음부터 다시 실행한다. [InnoDB 오류 처리](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)
- `SKIP LOCKED`의 빈 결과는 해당 시점에 잠글 수 있는 행을 찾지 못했다는 뜻이다. 잠겨서 건너뛴 행은 다른 폴링에서 조회될 수 있다. 두 옵션은 행 잠금에만 적용되므로 테이블 잠금이나 DDL과 충돌하는 메타데이터 잠금에서는 대기가 생길 수 있다. [MySQL 잠금 조회](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [MySQL 메타데이터 잠금](https://dev.mysql.com/doc/refman/8.4/en/metadata-locking.html)

두 세션 실습은 [Locking Reads with SKIP LOCKED](11_locking_reads_with_skip_locked.md), 잠금 조회의 기본 동작은 [Locking Reads with SELECT FOR UPDATE](31_locking_reads_with_select_for_update.md)를 참고한다.
