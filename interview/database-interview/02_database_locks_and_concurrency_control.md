# Database Locks and Concurrency Control

## 12. DB 락이란 무엇이고 어떤 종류가 있나요?

**30–60초 답변**

> DB 락은 여러 트랜잭션이 같은 자원에 접근할 때 서로 충돌하는 작업의 실행을 조정하는 장치입니다. 행이나 테이블처럼 보호 대상의 범위로 나눌 수 있고, 어떤 접근을 허용하는지에 따라 모드로도 나눌 수 있습니다. InnoDB에서 여러 트랜잭션이 같은 레코드의 공유 락(S)을 함께 보유할 수 있고, 배타 락(X)은 다른 트랜잭션의 S·X 락과 충돌합니다. InnoDB는 테이블에 의도 락을 잡아 어떤 행 락을 얻을지 표시하고, 조건과 격리 수준에 따라 삽입을 막는 갭 락이나 레코드와 앞쪽 갭을 함께 잠그는 넥스트 키 락도 사용합니다. [PostgreSQL 18의 명시적 잠금](https://www.postgresql.org/docs/18/explicit-locking.html) · [MySQL 8.4의 InnoDB 잠금](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)

**꼬리 질문 · 다른 트랜잭션이 행을 갱신하면 일반 `SELECT`도 기다리나요?**

PostgreSQL에서 일반 `SELECT`는 MVCC 스냅샷으로 보이는 행 버전을 읽으므로 같은 행의 갱신 락을 기다리지 않습니다. `SELECT FOR UPDATE`는 해당 행에 락을 얻어야 하므로 충돌하는 행 락이 풀릴 때까지 대기할 수 있습니다. `ALTER TABLE`이 획득할 수 있는 `ACCESS EXCLUSIVE` 같은 테이블 락은 일반 `SELECT`도 막을 수 있습니다. [PostgreSQL 18의 행·테이블 잠금 모드](https://www.postgresql.org/docs/18/explicit-locking.html)

## 13. 낙관적 락과 비관적 락은 어떻게 다른가요?

**30–60초 답변**

> 낙관적 락은 먼저 데이터를 읽고 작업한 뒤 갱신 시점에 다른 트랜잭션이 데이터를 바꿨는지 검증합니다. 예를 들어 읽었던 `version`을 `UPDATE` 조건에 넣고, 일치한 행을 바꾸면서 버전을 올립니다. 갱신된 행이 없다면 충돌이나 삭제를 확인하고 재시도 또는 실패를 처리합니다. 비관적 락은 `SELECT FOR UPDATE`처럼 값을 읽을 때 락을 얻어, 커밋이나 롤백까지 충돌하는 작업을 대기시킬 수 있습니다. 낙관적 락은 읽는 시점에 수정용 락을 선점하는 비용을 줄이고, 비관적 락은 읽은 값에 따른 판단을 하는 동안 해당 행의 변경을 막습니다. [Jakarta Persistence 3.2의 낙관적·비관적 잠금](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2) · [PostgreSQL 18의 행 잠금 모드](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS)

**꼬리 질문 · Jakarta Persistence의 `@Version`이 있으면 모든 수정 경로에서 자동으로 보호되나요?**

영속성 공급자가 버전 있는 엔티티를 갱신할 때 버전 검사를 수행합니다. JPQL 벌크 `UPDATE`는 자동 낙관적 락 검사를 우회하므로, 같은 보호가 필요하면 벌크 구문에 버전 조건과 버전 갱신을 직접 반영해야 합니다. 다른 SQL 수정 경로도 버전을 올려야 먼저 읽어 둔 버전이 오래됐음을 감지할 수 있습니다. [Jakarta Persistence 3.2의 엔티티 버전 및 벌크 갱신 규칙](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2)

## 14. 낙관적 락과 비관적 락은 각각 언제 쓰나요?

**30–60초 답변**

> 충돌이 드물고 실패한 변경을 사용자에게 보여 주거나 재시도할 수 있으면 낙관적 락이 어울립니다. 예를 들어 사용자가 프로필을 편집하는 동안 락을 잡아 두지 않고, 제출할 때 읽었던 버전이 여전히 유효한지 확인할 수 있습니다. 충돌이 잦고 갱신 전에 같은 행의 값을 읽어 결정해야 하며 트랜잭션이 짧다면 비관적 락을 고려합니다. 예를 들어 한 좌석의 예약 상태를 락으로 보호한 뒤 값을 확인하고 예약을 확정할 수 있습니다. 같은 행에 요청이 몰리면 비관적 락도 대기 시간을 늘리므로 충돌률과 재시도 비용, 실제 락 보유 시간을 함께 봅니다. [Jakarta Persistence 3.2의 잠금 모드](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2) · [PostgreSQL 18의 행 잠금과 교착상태](https://www.postgresql.org/docs/18/explicit-locking.html)

**꼬리 질문 · 재고 차감처럼 경합이 높은 기능이면 먼저 `SELECT FOR UPDATE`를 써야 하나요?**

상품 한 행의 재고가 양수일 때만 차감하면 된다면 `UPDATE stock SET quantity = quantity - 1 WHERE product_id = :id AND quantity > 0`처럼 조건과 변경을 한 문장에 넣을 수 있습니다. PostgreSQL의 `READ COMMITTED`에서는 같은 행의 앞선 갱신이 커밋되면 뒤의 `UPDATE`가 변경된 행에서 조건을 다시 평가합니다. 갱신 건수와 커밋 결과로 성공 여부를 판단합니다. [PostgreSQL 18의 Read Committed 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

## 15. 분산 락은 언제 필요하고 어떻게 동작하나요?

**30–60초 답변**

> 분산 락은 여러 프로세스가 같은 공유 자원에 대해 한 번에 한 작업만 진행하도록 조정할 때 사용합니다. 예를 들어 여러 워커가 같은 파일을 갱신한다면 파일 ID를 기준으로 락 키를 만들어 서로 다른 파일의 작업은 독립적으로 진행하게 합니다. 락 서비스가 획득을 중재하고, 작업자가 죽어도 락을 다시 얻을 수 있도록 임대에 만료 시간을 둡니다. 락을 해제하거나 연장할 때는 자신의 획득을 식별하는 소유권 값을 확인합니다. 중복 예약 방지처럼 조건이 한 DB 안에 있다면 `UNIQUE` 제약이나 조건부 `UPDATE`로 DB가 직접 보장하도록 설계할 수 있습니다. [Redis의 분산 락과 소유권 검증](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/) · [PostgreSQL 18의 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html) · [PostgreSQL 18의 조건부 갱신](https://www.postgresql.org/docs/18/sql-update.html)

**꼬리 질문 · 첫 락의 임대가 만료된 뒤 기존 작업자가 뒤늦게 쓰기를 보내면 어떻게 하나요?**

락을 획득할 때마다 증가하는 펜싱 토큰(fencing token)을 발급받아 쓰기 요청과 함께 보냅니다. 보호 대상 저장소는 자원별로 받아들인 가장 큰 토큰을 기록하고, 토큰 검사와 실제 갱신을 원자적으로 수행합니다. 예를 들어 새 작업자의 토큰 `42`를 받아들인 후에는 이전 작업자의 `41`을 거부합니다. 임대 만료는 다음 획득을 가능하게 하고, 지연된 쓰기를 막으려면 저장소가 토큰 검증을 지원해야 합니다. [Google Chubby 논문 §2.4의 시퀀서](https://research.google.com/archive/chubby-osdi06.pdf) · [Redis의 분산 락과 펜싱 토큰](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)

## 16. 갱신 유실(Lost Update)은 무엇이고 트랜잭션을 사용해도 발생하나요?

**30–60초 답변**

> 갱신 유실은 두 트랜잭션이 같은 값을 읽고 각각 계산한 뒤, 뒤의 쓰기가 앞의 변경을 덮어써 한쪽 갱신이 사라지는 현상입니다. 예를 들어 PostgreSQL의 `READ COMMITTED`에서 두 요청이 모두 재고 `10`을 읽고 각각 `SET quantity = 9`를 실행하면, 뒤의 쓰기도 미리 계산한 `9`를 써서 두 요청이 커밋해도 최종 재고는 `9`입니다. 보호 여부는 DB와 격리 수준에 따라 달라집니다. PostgreSQL의 `REPEATABLE READ`에서는 스냅샷 이후 다른 트랜잭션이 갱신하고 커밋한 같은 행을 수정하려 하면 직렬화 오류로 중단됩니다. [PostgreSQL 18의 트랜잭션 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html)

**꼬리 질문 · 갱신 유실과 쓰기 편향(Write Skew)은 어떻게 구분하나요?**

갱신 유실에서는 두 트랜잭션이 같은 행을 덮어씁니다. 쓰기 편향에서는 두 트랜잭션이 서로 다른 행을 바꾸면서 여러 행에 걸친 조건을 함께 깨뜨릴 수 있습니다. 예를 들어 당직자가 최소 한 명 있어야 하는데, 두 사람이 각각 상대방이 당직 중인 것을 읽고 자기 행만 당직 해제로 바꾸면 모두 빠질 수 있습니다. PostgreSQL의 `REPEATABLE READ`에서는 이런 쓰기 편향이 가능하고, `SERIALIZABLE`은 직렬 순서로 설명할 수 없는 실행을 감지해 트랜잭션을 실패시킵니다. [PostgreSQL 18의 Serializable 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-SERIALIZABLE)

## 17. 갱신 유실을 어떻게 방지할 수 있나요?

**30–60초 답변**

> 카운터 증가처럼 현재 값으로 계산할 수 있으면 `UPDATE counter SET value = value + 1 WHERE id = :id`처럼 읽기와 계산, 쓰기를 한 문장으로 처리합니다. 애플리케이션에서 값을 계산해야 한다면 `UPDATE`의 `WHERE`에 읽었던 `version`을 넣고, 갱신에 성공하면 같은 문장에서 버전을 올리는 비교 후 갱신(CAS)을 사용할 수 있습니다. 먼저 읽은 값으로 판단하는 동안 다른 쓰기를 막아야 할 때는 같은 트랜잭션 안에서 `SELECT FOR UPDATE`로 읽은 뒤 갱신합니다. 여러 행을 잠글 때는 범위를 필요한 행으로 좁히고 모든 경로에서 같은 순서로 락을 얻습니다. [PostgreSQL 18의 Read Committed 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED) · [Jakarta Persistence 3.2의 버전 검사](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2) · [PostgreSQL 18의 교착상태 처리](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS)

**꼬리 질문 · 락 충돌이나 직렬화 오류가 발생하면 실패한 SQL만 다시 실행하나요?**

재시도할 수 있는 직렬화 오류나 교착상태라면 기존 트랜잭션을 롤백하고 새 트랜잭션에서 읽기와 판단을 포함한 전체 작업을 다시 수행합니다. 재시도 횟수는 제한합니다. 버전 조건이 맞지 않아 갱신 건수가 `0`이라면 현재 값을 다시 읽어 변경을 재적용해도 되는지 확인합니다. 사용자 편집 결과처럼 변경을 자동 병합하기 어렵다면 충돌을 알려 사용자가 새 값을 확인하도록 할 수 있습니다. [PostgreSQL 18의 직렬화 실패 처리](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html) · [Jakarta Persistence 3.2의 낙관적 잠금](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2)
