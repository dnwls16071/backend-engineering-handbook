# SQL Transactions and Concurrency Control

트랜잭션은 주문 생성과 재고 차감처럼 함께 확정해야 하는 변경을 묶는다. `BEGIN`으로 시작해 성공하면 `COMMIT`하고, 업무 조건이 실패하면 `ROLLBACK`한다. 경합이 생기는 데이터에는 어떤 버전을 읽고 언제 쓰기를 막을지 결정해야 한다. SQL 예제는 PostgreSQL 18을 기준으로 한다. [PostgreSQL 18 · Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)

## 1. ACID와 격리 수준

- **원자성**(Atomicity)은 트랜잭션의 변경을 전부 반영하거나 전부 취소한다.
- **일관성**(Consistency)은 트랜잭션 전후에 제약과 업무 규칙을 만족하는 상태를 유지한다. 데이터베이스 제약으로 표현하기 어려운 규칙은 애플리케이션도 함께 지켜야 한다.
- **격리성**(Isolation)은 동시에 실행되는 트랜잭션이 서로의 변경을 관찰하는 범위와 충돌 처리 방식을 정한다.
- **지속성**(Durability)은 성공적으로 커밋한 변경을 장애 후에도 복구할 수 있게 한다. 실제 보장은 동기 커밋 같은 설정에 의존한다. [PostgreSQL 18 · Asynchronous Commit](https://www.postgresql.org/docs/18/wal-async-commit.html)

커밋 전 값을 읽는 현상이 더티 리드다. 같은 행을 다시 읽었을 때 값이 달라지면 반복 불가능 읽기, 같은 조건을 다시 조회했을 때 일치하는 행 집합이 달라지면 팬텀 읽기다. SQL 표준의 `READ COMMITTED`는 더티 리드를, `REPEATABLE READ`는 반복 불가능 읽기까지 차단한다. `SERIALIZABLE`에서 성공한 트랜잭션들의 결과는 어떤 직렬 실행 순서와 같아야 한다. 각 엔진은 표준보다 강한 보장이나 다른 구현 방식을 제공할 수 있다. [PostgreSQL 18 · Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)

| 엔진 | 기본 격리 수준 | 조회와 잠금의 특성 |
| --- | --- | --- |
| PostgreSQL 18 | `READ COMMITTED` | 일반 조회는 문장마다 스냅샷을 얻는다. `READ UNCOMMITTED`도 같은 동작을 한다. `REPEATABLE READ`는 트랜잭션 스냅샷을 유지해 팬텀을 막지만 직렬화 이상은 가능하다. |
| MySQL 8.4 InnoDB | `REPEATABLE READ` | 일반 조회는 첫 일관 읽기의 스냅샷을 재사용한다. 잠금 읽기나 DML의 범위 검색은 실행 조건에 따라 갭 락이나 넥스트 키 락을 건다. |
| SQL Server 2022 | `READ COMMITTED` | 기본적으로 공유 잠금으로 읽는다. DB의 `READ_COMMITTED_SNAPSHOT`을 켜면 문장 단위 행 버전을 읽는다. |
| Oracle Database 19c | `READ COMMITTED` | 일반 조회는 문장 시작 시점의 커밋된 버전을 본다. `SERIALIZABLE`에서는 트랜잭션 단위 읽기 일관성을 제공한다. |

[PostgreSQL 18 · Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) · [MySQL 8.4 · InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html) · [SQL Server · 격리 수준](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql?view=sql-server-ver16) · [Oracle 19c · Data Concurrency and Consistency](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html)

## 2. MVCC와 행 잠금

MVCC에서는 조회가 자신에게 보이는 행 버전을 선택한다. PostgreSQL의 일반 `SELECT`와 행 쓰기는 보통 서로를 기다리지 않지만, 같은 행에 대한 쓰기와 잠금 읽기는 충돌할 수 있다. 먼저 읽고 판단한 뒤 갱신해야 한다면 `SELECT ... FOR UPDATE`로 대상 행을 잡고 같은 트랜잭션에서 변경한다. 여러 행을 잠글 때 접근 순서를 일정하게 유지하면 교착 가능성이 낮아진다. [PostgreSQL 18 · MVCC](https://www.postgresql.org/docs/18/mvcc-intro.html) · [PostgreSQL 18 · Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)

### `SKIP LOCKED`로 작업 선점하기

작업자가 여러 명이면 잠긴 행을 건너뛰고 다음 `ready` 작업을 가져올 수 있다. 선점과 상태 갱신을 한 트랜잭션으로 묶고 커밋 뒤 실제 작업을 실행한다. [PostgreSQL 18 · SELECT 잠금 절](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)

```sql
CREATE TABLE job_queue (
    id bigint PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('ready', 'running', 'done'))
);
CREATE INDEX job_queue_ready_idx ON job_queue (id) WHERE status = 'ready';
INSERT INTO job_queue VALUES (1, 'ready'), (2, 'ready');

BEGIN;
WITH next_job AS (
    SELECT id
    FROM job_queue
    WHERE status = 'ready'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
UPDATE job_queue AS q
SET status = 'running'
FROM next_job
WHERE q.id = next_job.id
RETURNING q.id;
COMMIT;
```

첫 세션이 `COMMIT`하기 전에 두 번째 세션에서 `BEGIN`부터 실행하면 각각 ID 1과 2를 선점한다. 모든 후보가 잠겼으면 선점 결과가 0행일 수 있고, 잠긴 행을 건너뛰므로 엄격한 FIFO 순서는 보장되지 않는다. 운영 큐는 상태와 함께 선점 만료 시각을 저장해 작업자 종료로 남은 `running` 행을 회수할 수 있다. [PostgreSQL 18 · SELECT 잠금 절](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)

## 3. 2단계 잠금과 2단계 커밋

**2단계 잠금**(2PL)은 동시 실행 순서를 제어한다. 확장 단계에서 잠금을 얻고, 첫 잠금을 풀면 축소 단계에 들어가 새 잠금을 얻지 않는다. 이 규칙은 충돌 직렬성을 보장한다. [CMU 15-445 · Two-Phase Locking](https://15445.courses.cs.cmu.edu/spring2025/notes/17-twophaselocking.pdf)

**2단계 커밋**(2PC)은 분산 트랜잭션 참여자들이 동일한 커밋 또는 롤백 결정을 적용하도록 조정한다. 준비 단계에서 각 참여자가 커밋할 수 있는지 확인하고, 결정 단계에서 코디네이터의 결정을 적용한다. PostgreSQL은 외부 트랜잭션 관리자가 쓸 수 있도록 `PREPARE TRANSACTION`, `COMMIT PREPARED`, `ROLLBACK PREPARED`를 제공한다. 준비 상태에서도 잠금을 유지하므로 관리자가 미결 트랜잭션을 정리해야 한다. [PostgreSQL 18 · Two-Phase Transactions](https://www.postgresql.org/docs/18/two-phase.html) · [PostgreSQL 18 · PREPARE TRANSACTION](https://www.postgresql.org/docs/18/sql-prepare-transaction.html)

## 4. 버전 열을 이용한 낙관적 잠금과 재시도

상품 설명을 화면에 열어 둔 동안 잠금을 오래 유지하기는 어렵다. 조회 당시의 버전을 수정 요청에 넣고, `UPDATE`의 조건에서 현재 버전과 비교한다. 수정 경로마다 같은 규칙으로 버전을 증가시킨다. [PostgreSQL 18 · UPDATE](https://www.postgresql.org/docs/18/sql-update.html)

```sql
CREATE TABLE product_note (
    id bigint PRIMARY KEY,
    note text NOT NULL,
    version bigint NOT NULL DEFAULT 1
);
INSERT INTO product_note (id, note) VALUES (42, '초안');
SELECT note, version FROM product_note WHERE id = 42;

-- version 1을 읽은 수정 요청
UPDATE product_note
SET note = '검토 완료', version = version + 1
WHERE id = 42 AND version = 1
RETURNING version;
```

`READ COMMITTED`에서 같은 버전으로 다시 수정하면 0행을 반환한다. 대상이 삭제됐거나 버전이 달라졌으므로 다시 읽고 변경을 합칠지 결정한다. `40001` 직렬화 실패나 재시도 가능한 `40P01` 교착에 대해서는 롤백 뒤 읽기와 판단을 포함한 전체 트랜잭션을 제한된 횟수만큼 재실행한다. 재시도할 수 있는 작업에서 외부 호출을 한다면 커밋 확정 뒤에 실행하거나 멱등 키로 중복 효과를 막는다. [PostgreSQL 18 · Serialization Failure Handling](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html)
