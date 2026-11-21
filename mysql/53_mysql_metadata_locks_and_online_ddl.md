# MySQL Metadata Locks and Online DDL

MySQL 8.4에서 테이블 정의를 보호하는 메타데이터 락의 대기 줄을 읽는다. 배포용 연결에 짧은 대기 한도와 명시적인 DDL 알고리즘을 적용한 뒤 실행한다. [MySQL 메타데이터 락](https://dev.mysql.com/doc/refman/8.4/en/metadata-locking.html)

## 1. ALTER 한 줄이 이후 SELECT까지 기다리게 하는 과정

먼저 시작한 트랜잭션이 테이블의 공유 메타데이터 락을 보유하면, 같은 테이블을 ALTER하는 세션이 배타 메타데이터 락을 기다릴 수 있다. 대기 중인 배타 요청 때문에 뒤에 들어온 SELECT도 줄에 설 수 있다. 온라인 DDL도 정의 변경을 시작하거나 확정하는 단계에 메타데이터 락이 필요하다. [온라인 DDL과 메타데이터 락](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-performance.html)

격리된 실습 스키마에서 `CREATE TABLE mdl_lab (id INT PRIMARY KEY) ENGINE=InnoDB`를 실행한다. 세션 A에서 `START TRANSACTION; SELECT * FROM mdl_lab;`을 실행하고 열린 채 둔다. B에서 `SET SESSION lock_wait_timeout = 5` 후 `ALTER TABLE mdl_lab ADD COLUMN memo VARCHAR(60), ALGORITHM=INSTANT`를 실행한다. B가 대기하는 동안 C에서 같은 SELECT를 실행해 차단되는지 관찰한다. A를 롤백하면 락이 풀린다. A를 계속 열어 뒀다면 B는 대기 한도에 도달해 실패할 수 있다.

## 2. 앞에서 열린 트랜잭션 찾기

현재 실행 중인 SQL이 없어도 열린 트랜잭션은 조회한 테이블의 메타데이터 락을 보유할 수 있다. 대기 관계에서 차단 세션과 테이블을 찾고, 해당 연결의 트랜잭션과 요청 시작 시간을 대조한다. `waiting_pid`와 `blocking_pid`는 MySQL 연결 ID다. 내부 Performance Schema 스레드 ID와 혼동하지 않는다. [sys.schema_table_lock_waits](https://dev.mysql.com/doc/refman/8.4/en/sys-schema-table-lock-waits.html)

```sql
SELECT object_schema, object_name, waiting_pid, blocking_pid,
       waiting_lock_type, blocking_lock_type
FROM sys.schema_table_lock_waits
WHERE object_schema = DATABASE();
```

## 3. lock_wait_timeout으로 DDL 대기 제한하기

`lock_wait_timeout`은 메타데이터 락을 얻기까지의 대기를 제한한다. 여러 락을 각각 요청하면 문장 전체의 대기 시간은 설정값보다 길어질 수 있다. `innodb_lock_wait_timeout`은 InnoDB 행 락 대기의 한도다. 전용 배포 연결에서 다음처럼 세션 범위로 적용하고, 실패하면 차단 세션을 확인한 뒤 배포를 다시 시도할 시점을 정한다. [MySQL lock_wait_timeout](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_lock_wait_timeout)

```sql
SET SESSION lock_wait_timeout = 5;
```

## 4. 온라인 DDL 알고리즘을 명시하기

| 알고리즘 | 검토할 항목 |
| --- | --- |
| `INSTANT` | 지원되는 변경은 메타데이터 위주로 처리한다. `LOCK` 절을 붙인다면 `DEFAULT`만 가능하다. |
| `INPLACE` | 작업에 따라 테이블 재구성이 필요할 수 있다. `LOCK=NONE`을 지원하는 연산에서는 본 작업 중 일반 DML을 허용한다. |
| `COPY` | 새 테이블에 복사하는 경로다. 실행 시간과 쓰기 제한이 배포 계획에 맞는지 확인한다. |

알고리즘과 잠금 모드를 명시하면 작업이 지원하지 않을 때 오류로 확인할 수 있다. MySQL 8.4에서 같은 문장이라도 기존 테이블의 속성과 적용할 변경의 조합에 따라 지원 여부가 달라질 수 있다. 변경 대상과 동일한 테이블 정의에서 먼저 확인한다. [InnoDB 온라인 DDL 지원표](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html)

## 5. 배포 전 읽기 전용 점검 SQL

배포 대상 스키마를 선택한 관찰 연결에서 실행한다. 대기 중인 락이 없더라도 오래 열린 트랜잭션이 다음 DDL을 막을 수 있다. 점검으로 확인한 시점 이후에도 새 트랜잭션이 들어오므로 실제 배포 연결에 대기 한도를 유지한다.

```sql
SELECT trx_mysql_thread_id, trx_started,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS age_seconds,
       trx_state, trx_query
FROM information_schema.innodb_trx
ORDER BY trx_started;

SELECT OBJECT_NAME, LOCK_TYPE, LOCK_STATUS, OWNER_THREAD_ID
FROM performance_schema.metadata_locks
WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_SCHEMA = DATABASE()
ORDER BY OBJECT_NAME, LOCK_STATUS, OWNER_THREAD_ID;

SELECT object_name, waiting_pid, blocking_pid
FROM sys.schema_table_lock_waits
WHERE object_schema = DATABASE();
```

기존 차단 세션과 애플리케이션 요청을 연결한 뒤, 알고리즘 지원 여부, 대기 한도, 실패 후 재시도 조건을 확인한다. 이 쿼리는 연결을 종료하거나 락을 해제하지 않는다. [Performance Schema metadata_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-metadata-locks-table.html) · [sys.schema_table_lock_waits](https://dev.mysql.com/doc/refman/8.4/en/sys-schema-table-lock-waits.html)
