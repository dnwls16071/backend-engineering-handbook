# PostgreSQL Transaction Isolation and Locking

PostgreSQL 18과 MySQL 8.4 InnoDB의 기본 격리 수준을 비교하고, PostgreSQL에서 갱신 충돌과 잠금 대기를 진단한다. 동시성 실습은 같은 실습 데이터베이스에 접속한 별도 세션 두 개를 사용한다.

## 1. 기본 격리 수준과 스냅샷

PostgreSQL의 기본값은 READ COMMITTED이고, InnoDB의 기본값은 REPEATABLE READ다. PostgreSQL READ COMMITTED의 일반 SELECT는 문장마다 새 스냅샷을 사용한다. InnoDB REPEATABLE READ의 일반적인 일관 읽기는 첫 일관 읽기에서 정한 스냅샷을 재사용한다. 잠금 읽기는 별도 규칙으로 동작한다. 실제 연결 설정은 PostgreSQL의 `SHOW transaction_isolation`, MySQL의 `SELECT @@session.transaction_isolation`로 확인한다. [PostgreSQL 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html) · [InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

## 2. REPEATABLE READ 갱신 충돌과 SQLSTATE 40001

PostgreSQL에서는 트랜잭션의 스냅샷이 만들어진 후 다른 트랜잭션이 대상 행을 갱신하고 커밋하면, 해당 행을 갱신하려는 트랜잭션이 SQLSTATE `40001`로 실패할 수 있다. 같은 격리 수준 이름만 보고 엔진을 바꾼 뒤 쓰기의 결과가 같을 것으로 가정하면 충돌을 놓칠 수 있다. [PostgreSQL REPEATABLE READ](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-REPEATABLE-READ)

```sql
CREATE TABLE pg_lock_demo (
    id integer PRIMARY KEY,
    quantity integer NOT NULL CHECK (quantity >= 0)
);
INSERT INTO pg_lock_demo VALUES (1, 10), (2, 10);
```

1. 세션 A에서 `BEGIN ISOLATION LEVEL REPEATABLE READ` 후 `SELECT quantity FROM pg_lock_demo WHERE id = 1`을 실행해 스냅샷을 만든다.
2. 세션 B에서 `UPDATE pg_lock_demo SET quantity = quantity - 1 WHERE id = 1`을 실행하고 커밋한다.
3. 세션 A에서 같은 UPDATE를 실행한다. `40001`을 확인한 뒤 `ROLLBACK`한다.

재시도할 때는 새 트랜잭션에서 처음부터 데이터를 읽어 업무 조건을 다시 계산한다. 트랜잭션 안팎의 외부 작업 중복도 함께 고려한다. [직렬화 실패 처리](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html)

## 3. 범위의 불변식과 SERIALIZABLE

PostgreSQL의 행 잠금으로 조회한 빈 범위에 다른 트랜잭션이 INSERT하는 것을 막을 수 없다. 한 개만 허용되는 키는 UNIQUE 제약으로 표현하고, 여러 행의 읽기와 쓰기가 함께 지켜야 하는 조건은 SERIALIZABLE과 재시도를 검토한다. PostgreSQL의 Serializable Snapshot Isolation은 읽기와 쓰기의 의존성을 추적하며 직렬 실행으로 설명할 수 없는 조합을 찾아 트랜잭션을 실패시킨다. 이때 사용하는 predicate lock은 INSERT를 해당 범위에서 직접 대기시키지 않는다. [PostgreSQL SERIALIZABLE](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-SERIALIZABLE) · [InnoDB 잠금 유형](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)

## 4. FOR UPDATE, NOWAIT, SKIP LOCKED

| 방식 | 행 잠금 충돌 시 동작 |
| --- | --- |
| `FOR UPDATE` | 대상 행을 잠글 수 있을 때까지 기다릴 수 있다. |
| `FOR UPDATE NOWAIT` | 대상 행을 즉시 잠글 수 없으면 오류를 반환한다. |
| `FOR UPDATE SKIP LOCKED` | 당장 잠글 수 없는 행을 건너뛴다. 여러 소비자가 접근하는 큐에 사용할 수 있다. |

세션 A에서 트랜잭션을 열고 `id = 1`을 `FOR UPDATE`로 잠근다. 세션 B에서 아래 쿼리를 실행하면 1번을 건너뛰고 2번을 얻는다. 큐에서는 선택과 작업 상태 갱신을 한 트랜잭션으로 묶는다. `NOWAIT`와 `SKIP LOCKED`는 행 잠금에 적용되며 필요한 테이블 잠금에는 별도의 대기가 생길 수 있다. [PostgreSQL SELECT 잠금 절](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)

```sql
SELECT id
FROM pg_lock_demo
ORDER BY id
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

## 5. advisory lock으로 애플리케이션 작업 조율하기

같은 업무 키의 작업을 동시에 실행하지 않으려면 모든 실행 경로가 같은 advisory lock 키를 사용하게 한다. 키는 업무의 고유 식별자와 작업 유형에 맞춰 정의한다. 트랜잭션 수준 잠금은 커밋이나 롤백으로 해제된다. 세션 수준 잠금은 트랜잭션을 롤백해도 남으므로 커넥션 풀에서는 해제 시점을 특히 주의한다. [PostgreSQL advisory lock](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS)

```sql
BEGIN;
SELECT pg_advisory_xact_lock(100, 42);
SELECT quantity FROM pg_lock_demo WHERE id = 1;
COMMIT;
```

## 6. 트랜잭션 DDL과 잠금 대기 줄

많은 PostgreSQL DDL은 트랜잭션에서 되돌릴 수 있다. 아래 예의 컬럼은 롤백 뒤 남지 않는다. DDL이 요구하는 강한 잠금은 커밋이나 롤백까지 유지될 수 있다. 기존 조회가 DDL을 막고, 강한 잠금을 기다리는 DDL이 뒤에 들어온 조회를 막는 대기 줄도 생길 수 있다. `CREATE INDEX CONCURRENTLY`처럼 트랜잭션 블록에서 실행할 수 없는 명령은 별도로 처리한다. [PostgreSQL 잠금 모드](https://www.postgresql.org/docs/18/explicit-locking.html) · [CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

```sql
BEGIN;
ALTER TABLE pg_lock_demo ADD COLUMN memo text;
ROLLBACK;

SELECT pid, wait_event_type, wait_event, pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE datname = current_database() AND wait_event_type = 'Lock';
```

## 7. 세 가지 타임아웃의 적용 범위

| 설정 | 제한하는 시간 |
| --- | --- |
| `lock_timeout` | 개별 잠금 획득을 기다리는 시간 |
| `statement_timeout` | SQL 문장 실행에 허용하는 시간 |
| `idle_in_transaction_session_timeout` | 트랜잭션을 연 채 다음 클라이언트 명령을 기다리는 시간 |

잠금 대기와 문장 실행을 구분해서 제한하려면 보통 잠금 타임아웃을 더 짧게 둔다. 트랜잭션 안의 `SET LOCAL`을 사용하면 종료 후 설정이 되돌아간다. 유휴 트랜잭션 타임아웃은 연결 자체를 종료할 수 있으므로 풀의 연결 오류 처리도 확인한다. [PostgreSQL 세션 타임아웃](https://www.postgresql.org/docs/18/runtime-config-client.html)

```sql
BEGIN;
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '5s';
SET LOCAL idle_in_transaction_session_timeout = '15s';
SELECT quantity FROM pg_lock_demo WHERE id = 1;
COMMIT;
```

## 8. 데드락 메시지에서 순환 대기 찾기

SQLSTATE `40P01`이면 서버 로그의 `DETAIL`에서 각 PID가 어떤 잠금을 기다리는지 연결한다. A가 1번을 잡고 2번을, B가 2번을 잡고 1번을 요구하면 순환이 생긴다. PostgreSQL은 한 트랜잭션을 중단해 순환을 끊는다. 여러 행을 잠그는 경로의 획득 순서를 맞추고, 실패한 작업을 재시도할 수 있다면 새 트랜잭션에서 전체 작업을 다시 수행한다. [PostgreSQL 데드락](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS) · [PostgreSQL 오류 코드](https://www.postgresql.org/docs/18/errcodes-appendix.html)
