# Idempotent Order Processing in a Monolith

주문을 확정할 때 재고와 포인트를 함께 차감하는 경우를 기준으로 한다. 한 애플리케이션이 세 모듈과 하나의 DB를 사용하면 주문 생성, 재고 차감, 포인트 차감을 하나의 로컬 트랜잭션에 묶을 수 있다. [PostgreSQL · Transactions](https://www.postgresql.org/docs/17/tutorial-transactions.html) · [Spring Framework · Declarative Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative.html)

## 1. 주문의 불변식과 트랜잭션 경계

| 영역 | 모듈이 보장할 조건 |
| --- | --- |
| 주문 | 동일 고객의 동일 요청 키에 대해 주문 효과가 한 번만 발생한다. |
| 재고 | 유효한 상품의 가용 수량 범위에서만 차감한다. |
| 포인트 | 충분한 잔액을 확인하고 주문에 연결된 차감 내역을 남긴다. |

단일 모듈에서 주문·재고·포인트를 직접 다루기보다 애플리케이션 서비스가 각 모듈의 유스케이스를 호출한다. 같은 데이터소스와 로컬 트랜잭션에 참여시키고 실패 시 전체 변경을 롤백한다. Spring에서는 호출이 트랜잭션 프록시를 거치는지, 예외 종류별 롤백 규칙이 요구사항과 맞는지 확인한다. [Spring Framework · Rolling Back a Declarative Transaction](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html)

## 2. 같은 주문을 식별하고 중복 처리 막기

주문 접수 테이블에 `(customer_id, idempotency_key)` 유일 제약을 둔다. 같은 키로 다른 요청이 들어왔는지 판단하도록 정규화한 요청의 지문을 같이 기록한다. 아래 예시는 기존 테이블에서 해당 열을 `NOT NULL`로 정의했다고 가정한다. [PostgreSQL · Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)

```sql
ALTER TABLE orders
    ADD CONSTRAINT orders_customer_request_unique
    UNIQUE (customer_id, idempotency_key);
```

첫 트랜잭션이 유일 키로 주문 행을 선점한다. 예를 들어 PostgreSQL에서는 `INSERT ... ON CONFLICT DO NOTHING RETURNING id`가 행을 반환했을 때만 재고·포인트를 차감한다. 기본 `READ COMMITTED`에서 행을 얻지 못한 호출은 다음 조회 문으로 기존 주문을 읽고, 지문이 일치하면 해당 결과를 반환하고 다르면 충돌로 처리한다. 커밋 직후 응답을 잃어도 동일 키로 결과를 조회한다. [PostgreSQL · INSERT](https://www.postgresql.org/docs/17/sql-insert.html) · [PostgreSQL · Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html)

## 3. 재고·포인트 경쟁과 검증

동일 요청 키를 직렬화해도 서로 다른 주문이 같은 재고와 잔액을 동시에 소비할 수 있다. 재고가 충분할 때만 차감하는 조건부 갱신을 쓰거나, 재고 행을 `SELECT ... FOR UPDATE`로 잠근 뒤 같은 트랜잭션에서 검증과 차감을 진행한다. 여러 행을 잠글 때는 고정된 순서로 접근하고, 트랜잭션 동안 외부 네트워크 호출을 피한다. [PostgreSQL · Explicit Locking](https://www.postgresql.org/docs/17/explicit-locking.html)

- **같은 요청 두 건**. 주문 한 건과 재고·포인트 차감 한 건씩만 남는다.
- **서로 다른 주문이 마지막 재고 경쟁**. 한 건만 확정하고 재고는 음수가 되지 않는다.
- **재고 처리 후 포인트 부족**. 주문과 재고 차감이 롤백된다. 거절 결과도 재사용하려면 거절만 남기는 별도 상태 저장 규칙을 명시한다.
- **DB 커밋 뒤 HTTP 응답 유실**. 같은 키와 같은 입력으로 다시 호출하면 저장된 주문을 얻는다.

관련 문서 [Modular Monoliths with Hexagonal Boundaries](03_modular_monoliths_with_hexagonal_boundaries.md) · [Moving Order Processing from a Monolith to Microservices](21_moving_order_processing_from_a_monolith_to_microservices.md)
