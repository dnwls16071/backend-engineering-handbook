# Transactions, Isolation, and MVCC

## 3. 트랜잭션이란 무엇이고 ACID는 무엇을 보장하나요?

**30–60초 답변**

> 트랜잭션은 함께 성공하거나 함께 취소되어야 할 DB 작업을 묶은 단위입니다. 계좌 이체를 예로 들면 원자성(Atomicity)은 출금과 입금을 모두 반영하거나 모두 취소하는 성질입니다. 일관성(Consistency)은 성공한 트랜잭션이 잔액이나 참조 무결성처럼 정의된 규칙을 유지한다는 뜻입니다. 데이터베이스 제약과 애플리케이션 로직이 그 규칙을 구현합니다. 격리성(Isolation)은 동시에 실행되는 트랜잭션이 서로의 변경을 언제 관찰할 수 있는지 정하며, 구체적인 보장은 격리 수준에 따릅니다. 지속성(Durability)은 커밋된 결과를 장애 이후에도 복구할 수 있다는 성질로, 실제 장애 대응 범위는 로그 동기화 설정과 저장장치에 따라 달라집니다. [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [MySQL 8.4 InnoDB와 ACID](https://dev.mysql.com/doc/refman/8.4/en/mysql-acid.html)

**꼬리 질문 · ACID의 일관성과 CAP의 일관성은 어떻게 다른가요?**

ACID의 일관성은 트랜잭션 전후 데이터가 정의된 무결성 규칙을 만족하는지를 말합니다. CAP의 일관성은 분산 저장소의 읽기와 쓰기가 실시간 순서를 지키면서 하나의 복사본에서 일어난 것처럼 보이는 선형화 가능성을 뜻합니다. 예를 들어 복제 지연으로 이전 값이 읽혀도 각 복사본의 무결성 제약은 여전히 만족할 수 있습니다. [PostgreSQL 18 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html) · [MySQL 8.4 그룹 복제의 일관성 보장](https://dev.mysql.com/doc/refman/8.4/en/group-replication-understanding-consistency-guarantees.html)

**꼬리 질문 · MySQL에서 커밋의 지속성을 확인하려면 어떤 설정을 보나요?**

`innodb_flush_log_at_trx_commit=1`은 커밋마다 InnoDB redo 로그를 기록하고 디스크에 동기화합니다. 바이너리 로깅을 쓰면 `sync_binlog=1`도 확인합니다. 운영체제와 저장장치가 동기화 요청을 실제로 이행해야 이 설정이 의도한 지속성을 얻습니다. [MySQL 8.4 InnoDB 시스템 변수](https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html#sysvar_innodb_flush_log_at_trx_commit) · [MySQL 8.4 바이너리 로깅 옵션](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html#sysvar_sync_binlog)

## 4. 트랜잭션을 사용할 때 어떤 점에 주의해야 하나요?

**30–60초 답변**

> 같은 규칙을 지키는 데 필요한 읽기와 쓰기를 한 트랜잭션에 묶고, 락을 획득한 뒤 커밋까지 걸리는 시간을 줄입니다. 예를 들어 재고를 차감한 직후 트랜잭션 안에서 외부 API를 호출하면 응답을 기다리는 동안 다른 요청도 해당 재고의 락을 기다릴 수 있습니다. 실패할 때는 어느 범위까지 롤백됐는지 확인해야 합니다. MySQL InnoDB에서 교착 상태의 희생 트랜잭션은 전체가 롤백되지만, 기본 설정에서 락 대기 시간 초과는 실패한 문장만 롤백합니다. 작업 단위 전체가 실패해야 한다면 이때 애플리케이션이 트랜잭션을 롤백해야 합니다. `ALTER TABLE`처럼 암묵적 커밋을 일으키는 MySQL 문장도 경계에 영향을 줍니다. [MySQL 8.4 InnoDB 오류 처리](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html) · [MySQL 8.4 암묵적 커밋을 일으키는 문장](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)

**꼬리 질문 · 주문 저장과 메시지 발행을 함께 처리하다가 주문 트랜잭션이 롤백되면 어떻게 되나요?**

DB 롤백은 그 트랜잭션의 DB 변경에 적용됩니다. 외부 브로커가 이미 받은 메시지는 브로커에 남습니다. 트랜잭셔널 아웃박스를 쓰면 주문과 발행할 메시지의 레코드를 같은 DB 트랜잭션에 기록하고, 별도 발행기가 커밋된 레코드를 읽어 브로커에 전송합니다. 발행 후 처리 상태를 기록하기 전에 발행기가 중단되면 다시 전송할 수 있으므로, 이벤트 ID를 기준으로 중복 처리를 방지합니다. [PostgreSQL 18 트랜잭션의 커밋과 롤백](https://www.postgresql.org/docs/18/tutorial-transactions.html)

## 5. SQL의 트랜잭션 격리 수준 네 가지는 어떻게 다른가요?

**30–60초 답변**

> SQL 표준의 최소 보장 기준에서 `READ UNCOMMITTED`는 더티 리드, 반복 불가능 읽기, 팬텀 리드를 모두 허용할 수 있습니다. `READ COMMITTED`는 더티 리드를 막고, `REPEATABLE READ`는 반복 불가능 읽기까지 막지만 팬텀 리드는 허용할 수 있습니다. `SERIALIZABLE`은 이 세 현상을 막으며, 성공한 트랜잭션들의 결과가 어떤 순서로 하나씩 실행한 것과 같음을 보장합니다. 격리 수준 이름이 같아도 DB가 표준보다 강한 보장을 제공할 수 있습니다. PostgreSQL 18은 `READ UNCOMMITTED`를 `READ COMMITTED`처럼 처리하고, `REPEATABLE READ`에서 팬텀 리드도 막습니다. [PostgreSQL 18 격리 수준 표](https://www.postgresql.org/docs/18/transaction-iso.html#MVCC-ISOLEVEL-TABLE)

**꼬리 질문 · `READ COMMITTED`에서 한 트랜잭션으로 여러 번 읽으면 같은 시점의 데이터를 보나요?**

PostgreSQL 18의 일반 `SELECT`와 MySQL 8.4 InnoDB의 일관 읽기는 이 수준에서 문장마다 새 스냅샷을 사용합니다. 두 `SELECT` 사이에 다른 트랜잭션이 커밋하면 같은 조건으로 조회해도 두 번째 결과가 달라질 수 있습니다. 두 쿼리의 결과를 하나의 보고서에서 동일한 시점 기준으로 합쳐야 한다면, 한 문장으로 조회하거나 해당 DB의 트랜잭션 단위 스냅샷을 쓰는 방법을 고려합니다. [PostgreSQL 18의 Read Committed](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED) · [MySQL 8.4 InnoDB 일관 비잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html)

## 6. 더티 리드, 반복 불가능 읽기, 팬텀 리드는 어떻게 구분하나요?

**30–60초 답변**

> 더티 리드(Dirty Read)는 다른 트랜잭션이 아직 커밋하지 않은 변경을 읽는 현상입니다. 예를 들어 B가 잔액을 100원에서 80원으로 바꿨을 때 A가 80원을 읽고, 이후 B가 롤백하는 경우입니다. 반복 불가능 읽기(Nonrepeatable Read)는 A가 같은 계좌를 다시 읽었을 때 그사이 B가 커밋한 변경 때문에 잔액이 달라지는 현상입니다. 팬텀 리드(Phantom Read)는 같은 조건에 맞는 행의 집합이 달라지는 현상입니다. 예를 들어 A가 미결제 주문을 조회한 뒤 B가 새 미결제 주문을 넣고 커밋하면, A의 다음 조회에 그 주문이 들어올 수 있습니다. [PostgreSQL 18 격리 수준과 읽기 이상 현상](https://www.postgresql.org/docs/18/transaction-iso.html)

**꼬리 질문 · 다른 트랜잭션이 `INSERT`하지 않고 `UPDATE`만 해도 팬텀이 생기나요?**

생길 수 있습니다. A가 `WHERE status = 'PENDING'`으로 주문을 조회한 후, B가 기존 주문의 상태를 `PENDING`으로 바꾸고 커밋하면 A의 다음 조회에 그 주문이 새로 포함될 수 있습니다. 팬텀 리드의 판단 기준은 다른 트랜잭션의 커밋으로 같은 조건을 만족하는 행 집합의 구성원이 바뀌는지입니다. [PostgreSQL 18 팬텀 리드 정의](https://www.postgresql.org/docs/18/transaction-iso.html)

## 7. 트랜잭션에서 발생하는 동시성 이상은 어떻게 해결하나요?

**30–60초 답변**

> 보호할 규칙에 맞춰 방법을 고릅니다. 재고가 음수가 되면 안 되는 경우 `UPDATE inventory SET stock = stock - 1 WHERE id = ? AND stock > 0`으로 조건 확인과 차감을 묶고, 변경 행 수로 성공 여부를 확인할 수 있습니다. 기존 행을 읽고 판단한 뒤 수정해야 하면 같은 트랜잭션에서 `SELECT ... FOR UPDATE`로 그 행을 잠글 수 있습니다. 같은 좌석이 중복 예약되면 안 되는 규칙은 좌석 식별자에 `UNIQUE` 제약을 두어 동시 삽입에도 적용합니다. 여러 행을 함께 읽어야 지킬 수 있는 규칙은 관련 경로에서 공통으로 쓰는 락이나 `SERIALIZABLE`을 선택할 수 있습니다. 직렬화 실패가 나면 읽기와 판단을 포함한 트랜잭션 전체를 처음부터 재시도합니다. [PostgreSQL 18 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html) · [PostgreSQL 18 명시적 잠금](https://www.postgresql.org/docs/18/explicit-locking.html) · [PostgreSQL 18 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html) · [PostgreSQL 18 직렬화 실패 처리](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html)

**꼬리 질문 · 같은 좌석을 이미 예약한 사람이 있는지 `SELECT ... FOR UPDATE`로 확인하면 중복을 막을 수 있나요?**

PostgreSQL에서 예약 행을 조회했는데 결과가 비어 있으면 그 쿼리가 잠글 예약 행도 없습니다. 두 요청 모두 빈 결과를 보고 삽입을 시도할 수 있으므로 예약 테이블에 `NOT NULL`인 좌석 식별자와 `UNIQUE` 제약을 두면 DB가 중복 삽입을 거부합니다. 이미 존재하는 좌석 행을 잠그는 방법도 있습니다. 예를 들어 PostgreSQL의 `READ COMMITTED`에서는 모든 예약 경로가 같은 좌석 행을 먼저 잠근 후, 별도 문장으로 예약 상태를 조회하고 결정하게 할 수 있습니다. [PostgreSQL 18 행 수준 잠금](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS) · [PostgreSQL 18 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html) · [PostgreSQL 18의 Read Committed](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

## 8. MVCC란 무엇이고 어떤 비용이 있나요?

**30–60초 답변**

> MVCC(Multi-Version Concurrency Control)는 행의 여러 버전을 관리하고 읽기의 스냅샷에 보이는 버전을 고르는 방식입니다. 다른 트랜잭션이 행을 수정 중이어도 일반 스냅샷 읽기는 자신에게 보이는 이전 버전을 읽을 수 있어 읽기와 쓰기 사이의 대기를 줄입니다. 쓰기끼리 충돌하면 행 잠금이나 충돌 처리가 필요할 수 있습니다. InnoDB는 변경 이력을 undo 로그에 보관해 필요할 때 이전 버전을 재구성하고, PostgreSQL은 갱신 전 행 버전을 보존했다가 `VACUUM`으로 공간을 재사용할 수 있게 합니다. 오래된 스냅샷이 계속 필요하면 버전 정리가 늦어지고 저장 공간과 읽기 비용이 늘 수 있습니다. [MySQL 8.4 InnoDB 다중 버전 관리](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html) · [PostgreSQL 18 동시성 제어 소개](https://www.postgresql.org/docs/18/mvcc-intro.html) · [PostgreSQL 18 VACUUM과 공간 회수](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-SPACE-RECOVERY)

**꼬리 질문 · 읽기만 하는 트랜잭션도 오래 열어 두면 문제가 되나요?**

오래된 스냅샷을 유지하는 읽기 트랜잭션은 자신의 데이터를 직접 변경하지 않아도 다른 트랜잭션이 만든 이전 버전의 정리를 늦출 수 있습니다. 예를 들어 InnoDB에서 `REPEATABLE READ`의 일관 읽기가 스냅샷을 잡은 채 열려 있으면, 그 스냅샷에 필요한 버전을 재구성할 수 있도록 관련 update undo 로그를 보존합니다. 그사이 갱신이 계속되면 undo 이력이 늘어날 수 있습니다. [MySQL 8.4 InnoDB 다중 버전 관리](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html) · [MySQL 8.4 InnoDB 트랜잭션 관리](https://dev.mysql.com/doc/refman/8.4/en/optimizing-innodb-transaction-management.html)

## 9. InnoDB의 `REPEATABLE READ`에서는 팬텀 리드를 어떻게 막나요?

**30–60초 답변**

> 일반 `SELECT`가 하는 일관 읽기는 같은 트랜잭션에서 같은 스냅샷을 재사용합니다. 다른 트랜잭션이 조건에 맞는 행을 추가하고 커밋해도, 먼저 스냅샷을 만든 트랜잭션에서 같은 일관 읽기를 반복하면 그 행은 보이지 않습니다. `SELECT ... FOR UPDATE` 같은 잠금 읽기로 범위를 조회할 때는 실제로 스캔하는 인덱스 범위에 갭 락이나 넥스트 키 락을 걸어 다른 트랜잭션의 범위 내 삽입을 막습니다. 넥스트 키 락은 인덱스 레코드 락과 그 레코드 바로 앞의 갭 락을 합친 잠금입니다. [MySQL 8.4 InnoDB 일관 비잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html) · [MySQL 8.4 InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html) · [MySQL 8.4 InnoDB 넥스트 키 락](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html#innodb-next-key-locks)

**꼬리 질문 · 기본 키가 10과 20인 행 사이에 다른 트랜잭션이 15를 삽입할 수 있나요?**

`REPEATABLE READ`에서 A가 일반 `SELECT`로 기본 키 10부터 20까지를 먼저 읽었다면 B는 15를 삽입하고 커밋할 수 있습니다. A의 기존 스냅샷에는 15가 나타나지 않습니다. A가 범위의 첫 조회를 `SELECT ... FOR UPDATE`로 하고 기본 키 인덱스로 해당 범위를 스캔했다면, B의 15 삽입은 그 위치를 덮는 갭의 잠금이 풀릴 때까지 기다립니다. [MySQL 8.4 InnoDB 일관 비잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html) · [MySQL 8.4 InnoDB의 팬텀 행](https://dev.mysql.com/doc/refman/8.4/en/innodb-next-key-locking.html)

## 10. InnoDB의 `REPEATABLE READ`를 사용할 때 어떤 동작을 추가로 확인해야 하나요?

**30–60초 답변**

> `START TRANSACTION`으로 시작한 InnoDB `REPEATABLE READ` 트랜잭션은 보통 첫 일관 비잠금 읽기에서 스냅샷을 만듭니다. 시작 시점의 스냅샷이 필요하면 `START TRANSACTION WITH CONSISTENT SNAPSHOT`을 사용할 수 있습니다. 한 트랜잭션 안에서 일관 읽기와 잠금 읽기를 섞으면 서로 다른 버전이 보일 수 있습니다. 예를 들어 A가 일반 `SELECT`로 잔액 100을 읽은 뒤 B가 150으로 바꾸고 커밋하면, A의 `SELECT ... FOR UPDATE`는 150을 읽고 잠글 수 있습니다. A가 직접 변경하지 않았다면 이후 일반 `SELECT`는 다시 기존 스냅샷의 100을 볼 수 있습니다. [MySQL 8.4 트랜잭션 시작과 스냅샷 옵션](https://dev.mysql.com/doc/refman/8.4/en/commit.html) · [MySQL 8.4 InnoDB 일관 비잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html) · [MySQL 8.4 InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

**꼬리 질문 · 기본 키로 한 건을 잠그는 경우와 인덱스 범위를 잠그는 경우는 어떻게 다르고, `READ COMMITTED`에서는 어떻게 되나요?**

InnoDB `REPEATABLE READ`에서 기본 키의 등호 조건으로 기존 행 한 건을 찾으면 해당 인덱스 레코드에만 락이 걸립니다. 복합 고유 인덱스의 일부 열만 조회하거나 범위 조건을 쓰면 실제로 스캔한 인덱스 범위에 갭 락이나 넥스트 키 락을 사용할 수 있습니다. 적합한 인덱스가 없어 전체를 스캔하면 잠금 범위도 넓어질 수 있으므로 실행 계획에서 접근 경로를 확인합니다. `READ COMMITTED`에서는 잠금 읽기와 `UPDATE`·`DELETE`가 일반적으로 레코드 락을 사용하고, 외래 키와 중복 키 검사에는 갭 락이 쓰일 수 있습니다. 같은 범위를 잠금 읽기로 조회해도 다른 트랜잭션이 범위 안에 새 행을 삽입할 수 있습니다. [MySQL 8.4 InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html) · [MySQL 8.4 InnoDB 잠금 종류](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) · [MySQL 8.4 SQL 문장별 잠금 범위](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)
