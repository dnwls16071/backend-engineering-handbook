# Transaction Isolation and Locking Patterns

트랜잭션은 함께 성공하거나 함께 실패해야 하는 DB 연산의 범위를 정한다. 경합이 있는 쓰기는 격리 수준과 잠금 방식, 충돌 후 재시도 경계까지 설계한다. [Jakarta Persistence 3.1 §3.4](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [PostgreSQL 트랜잭션 격리](https://www.postgresql.org/docs/17/transaction-iso.html)

## 1. 트랜잭션 경계와 동시성 문제

재고를 읽어 주문 가능 여부를 판단하고 차감하는 작업에는 읽기와 쓰기 사이에 경쟁 요청이 들어올 수 있다. 단일 행의 불변식이라면 아래처럼 조건과 UPDATE를 한 문장으로 묶고 갱신 행 수를 검사할 수 있다. 주문 생성도 함께 성공해야 한다면 같은 트랜잭션 안에 둔다. 자동 재시도가 외부 결제나 메시지 중복을 일으키지 않도록 DB 경계와 외부 부수 효과를 따로 설계한다.

```sql
UPDATE inventory
SET quantity = quantity - 1
WHERE id = 42 AND quantity >= 1;
```

## 2. ACID (1) — 원자성과 일관성

원자성은 트랜잭션의 쓰기가 함께 커밋되거나 롤백되는 성질이다. 일관성은 허용된 상태에서 다른 허용된 상태로 이동한다는 의미다. 재고가 음수가 될 수 없다는 규칙은 DB의 CHECK로 보강하고, 여러 행 사이의 결제 한도 같은 규칙은 모델과 동시성 제어를 함께 설계한다. [PostgreSQL 트랜잭션](https://www.postgresql.org/docs/17/tutorial-transactions.html) · [PostgreSQL 제약](https://www.postgresql.org/docs/17/ddl-constraints.html)

## 3. ACID (2) — 격리성과 지속성

PostgreSQL의 READ COMMITTED에서는 연속한 두 SELECT가 각각 문장 시작 시점의 스냅샷을 볼 수 있다. REPEATABLE READ는 같은 트랜잭션에서 일관된 스냅샷을 제공하지만 여러 행에 걸친 규칙의 직렬화 이상까지 일반적으로 막지는 않는다. SERIALIZABLE에서 직렬화 충돌로 실패하면 새 트랜잭션에서 전체 판단과 쓰기를 재시도한다. 지속성은 커밋된 결과가 장애 뒤에도 보존되는 성질로, WAL과 커밋 설정에 영향을 받는다. [PostgreSQL 트랜잭션 격리](https://www.postgresql.org/docs/17/transaction-iso.html) · [PostgreSQL WAL 설정](https://www.postgresql.org/docs/17/runtime-config-wal.html)

## 4. 비관적 잠금

활성 트랜잭션에서 `em.find(Inventory.class, id, LockModeType.PESSIMISTIC_WRITE)`로 행 잠금을 요청할 수 있다. Hibernate가 PostgreSQL에서 어떤 잠금 구문을 생성하는지 확인한다. 경쟁 쓰기는 잠금 해제를 기다리거나 타임아웃 등으로 실패할 수 있으므로 잠금 구간을 짧게 유지하고 여러 행은 일관된 순서로 잠근다. 존재하지 않는 행이나 행 집합 전체에 관한 규칙에는 별도의 제약 또는 적절한 격리 전략이 필요하다. [Jakarta Persistence 3.1 §3.4.4](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [PostgreSQL 행 잠금](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-ROWS)

## 5. 낙관적 잠금

```java
@Version
private Long version;
```

Hibernate가 관리 엔티티를 갱신할 때 보통 ID와 조회 시점의 버전을 UPDATE 조건에 넣는다. 다른 트랜잭션이 먼저 갱신했다면 조건과 맞는 행이 없어져 플러시나 커밋에서 낙관적 잠금 실패가 드러날 수 있다. 새 트랜잭션에서 최신 값을 읽고 업무 규칙을 다시 평가한다. 분리 객체나 클라이언트가 보낸 변경을 처리할 때도 어떤 버전을 수정하려 했는지 유지해야 한다. 한 행의 버전만으로 여러 행 사이의 불변식을 보호할 수는 없다. [Jakarta Persistence 3.1 §3.4.2](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)
