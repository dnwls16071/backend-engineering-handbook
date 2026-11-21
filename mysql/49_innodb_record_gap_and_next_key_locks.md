# InnoDB Record, Gap, and Next-Key Locks

MySQL 8.4 InnoDB에서 잠금 범위는 SQL 조건뿐 아니라 선택한 인덱스와 격리 수준에 따라 달라진다. 아래 예제는 별도의 실습 데이터베이스와 두 SQL 연결을 사용한다. [InnoDB 잠금 유형](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)

## 1. UPDATE가 획득하는 레코드 락

InnoDB는 인덱스 레코드에 레코드 락을 건다. 존재하는 행을 완전한 기본 키 등호로 찾는 UPDATE는 검색한 기본 키 레코드에 배타 락을 건다. 보조 인덱스를 통해 찾으면 관련 클러스터드 인덱스 레코드도 잠글 수 있다. 보조 인덱스 갱신이나 제약 검사도 별도의 잠금을 요구할 수 있다. [SQL 문장별 InnoDB 잠금](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)

## 2. 인덱스가 없을 때 잠금 범위가 넓어지는 이유

잠금이 필요한 문장은 접근 경로를 따라 검사한 인덱스 레코드에 잠금을 설정한다. 조건에 쓸 인덱스가 없어 넓게 스캔하면 REPEATABLE READ에서 결과에 포함되지 않은 레코드도 잠금의 영향을 받을 수 있다. UPDATE에 `EXPLAIN`을 적용해 선택한 키와 예상 접근 범위를 보고, 실행 중 잠금은 `performance_schema.data_locks`에서 확인한다. [InnoDB 잠금과 접근 경로](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)

## 3. 갭 락과 넥스트키 락

갭 락은 인덱스 키 사이의 빈 구간에 새 키를 삽입하지 못하게 한다. 같은 갭의 갭 락끼리는 공존할 수 있다. 넥스트키 락은 레코드 락과 그 직전 갭 락을 함께 잡는다. 키가 10, 20, 30이라면 20에 대한 넥스트키 락의 예는 `(10, 20]`이다. 경계의 실제 잠금은 선택한 인덱스와 스캔 범위를 확인한다. 유일 키 등호 검색이라도 찾는 행이 없으면 REPEATABLE READ의 잠금 읽기에서 갭이 잠길 수 있다. [InnoDB 갭과 넥스트키 락](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)

## 4. 격리 수준에 따라 달라지는 잠금 범위

InnoDB REPEATABLE READ에서 범위 잠금 읽기는 범위에 대한 새 삽입을 막을 수 있다. READ COMMITTED에서는 검색과 인덱스 스캔에 갭 락을 일반적으로 쓰지 않으며, 외래 키 검사와 중복 키 검사는 예외다. READ COMMITTED에서 조건을 만족하지 않는 레코드 락은 WHERE 평가 후 풀릴 수 있다. 같은 변경을 여러 격리 수준에서 실행해 조회 결과와 대기를 함께 비교한다. [InnoDB 트랜잭션 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

## 5. 일관 읽기와 잠금 읽기

일반 SELECT는 READ COMMITTED와 REPEATABLE READ에서 스냅샷의 커밋 버전을 읽는 일관 읽기다. REPEATABLE READ는 일반적으로 처음 일관 읽기의 스냅샷을 재사용하고, READ COMMITTED는 문장마다 새 스냅샷을 사용한다. `FOR SHARE`와 `FOR UPDATE`는 잠금 읽기이며 다른 트랜잭션의 변경이 끝날 때까지 대기할 수 있다. 두 방식을 한 트랜잭션에서 섞으면 관찰하는 행의 버전이 다를 수 있다. [일관된 비잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html) · [잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

## 6. 실습 · 네 가지 잠금 상황 재현하기

```sql
CREATE TABLE innodb_lock_lab (
    id INT PRIMARY KEY,
    marker VARCHAR(20) NOT NULL,
    qty INT NOT NULL
) ENGINE = InnoDB;

INSERT INTO innodb_lock_lab VALUES (10, 'other', 5), (20, 'target', 5), (30, 'other', 5);
```

두 연결에서 `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ`와 `SET SESSION innodb_lock_wait_timeout = 3`을 실행한다. 각 행은 독립 실험이다. A가 트랜잭션을 열고 문장을 실행한 뒤, B도 트랜잭션을 열고 충돌 문장을 실행한다. 기다리거나 타임아웃이 발생하는지 확인하고 두 연결을 모두 롤백한다.

| 잠금 | 세션 A | 세션 B |
| --- | --- | --- |
| 레코드 | `UPDATE innodb_lock_lab SET qty = qty - 1 WHERE id = 20` | 같은 키의 UPDATE |
| 인덱스 없는 스캔 | `UPDATE innodb_lock_lab SET qty = qty - 1 WHERE marker = 'target'` | `UPDATE innodb_lock_lab SET qty = qty - 1 WHERE id = 30` |
| 빈 갭 | `SELECT id FROM innodb_lock_lab WHERE id = 15 FOR UPDATE` | `INSERT INTO innodb_lock_lab VALUES (15, 'new', 5)` |
| 레코드와 갭 | `SELECT id FROM innodb_lock_lab FORCE INDEX (PRIMARY) WHERE id BETWEEN 11 AND 20 FOR UPDATE` | 20번 행의 UPDATE와 15번 행의 INSERT를 각각 확인 |

다른 관찰 연결에서 다음 SQL로 잠금을 확인한다. `LOCK_DATA`는 진단 값이며 페이지 상태에 따라 NULL일 수 있다. [Performance Schema data_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html)

```sql
SELECT INDEX_NAME, LOCK_TYPE, LOCK_MODE, LOCK_STATUS, LOCK_DATA
FROM performance_schema.data_locks
WHERE OBJECT_SCHEMA = DATABASE() AND OBJECT_NAME = 'innodb_lock_lab';
```
