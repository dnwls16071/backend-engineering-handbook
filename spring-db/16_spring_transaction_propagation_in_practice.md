# Spring Transaction Propagation in Practice

## 1. 상품 등록과 시도 기록의 커밋 정책 정하기

상품과 필수 등록 이력을 함께 확정해야 한다면 하나의 트랜잭션에 저장한다. 이후 상품 등록이 실패해도 요청 시도 자체를 남겨야 한다면 시도 기록에 독립 트랜잭션을 사용할 수 있다. 이때 시도 기록에는 별도의 요청 식별자를 저장한다. 바깥 트랜잭션이 방금 추가한 상품의 미커밋 행을 내부 트랜잭션에서 참조하면 조회나 잠금 문제가 생길 수 있다. [Spring Framework 6.2 · REQUIRED와 REQUIRES_NEW](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/tx-propagation.html)

| 상황 | 전파 설정과 결과 |
| --- | --- |
| 상품과 필수 이력을 함께 확정 | 내부 작업도 `REQUIRED`로 참여한다. 서로 다른 빈의 작업이 같은 물리 트랜잭션에 들어간다. |
| 내부의 런타임 예외를 바깥에서 잡음 | 내부가 `REQUIRED`이면 바깥 커밋에서 `UnexpectedRollbackException`이 발생할 수 있다. |
| 시도 기록을 독립적으로 확정 | 내부를 `REQUIRES_NEW`로 실행한다. 내부 커밋 이후 상품 등록이 롤백돼도 시도 기록은 남는다. |
| 시도 기록의 실패에도 상품 등록을 계속 진행 | 독립 트랜잭션이 롤백한 뒤, 바깥은 업무 정책상 처리 가능한 예외만 잡아 후속 처리를 한다. |

## 2. 별도 빈에 시도 기록 경계 두기

아래 예제는 `catalog_registration_attempt`에 등록 시도를 한 번 기록한다. 해당 테이블에는 `request_id VARCHAR(64) PRIMARY KEY`와 `item_name VARCHAR(100) NOT NULL`을 둔다. 상품 등록 서비스는 이 객체를 Spring 빈으로 주입받아 호출한다. `request_id` 중복을 재시도로 처리할지는 서비스의 멱등성 계약에 따라 결정한다.

```java
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

public class CatalogAttemptWriter {

    private final JdbcTemplate jdbc;

    public CatalogAttemptWriter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void record(String requestId, String itemName) {
        jdbc.update("""
                INSERT INTO catalog_registration_attempt (request_id, item_name)
                VALUES (?, ?)
                """, requestId, itemName);
    }
}
```

바깥 서비스에서 `record(...)`를 호출한 뒤 상품 등록 로직이 실패하면 요청 시도 행은 남고 상품 행은 롤백된다. 내부 호출에 실패해도 상품을 저장할 수 있는 업무라면 대상 예외만 외부 서비스에서 처리한다. 테스트에서는 상품과 시도 기록을 서로 다른 테이블에서 조회해 실제 커밋 결과를 각각 확인한다. [Spring Framework 6.2 · 트랜잭션 전파](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/tx-propagation.html)

## 3. 커밋 후에 실행할 작업 구분하기

상품 등록이 커밋된 뒤에만 알림을 보내야 한다면 `@TransactionalEventListener`의 `AFTER_COMMIT` 단계에 처리기를 연결할 수 있다. 전송할 이벤트도 상품과 함께 영속 저장해야 한다면 같은 트랜잭션에 아웃박스 행을 저장하고 별도 발행 작업에서 처리한다. [Spring Framework 6.2 · 트랜잭션에 연결된 이벤트](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/event.html) · [트랜잭셔널 아웃박스](../engineering-design-training/06_publishing_events_reliably_with_the_transactional_outbox_pattern.md)
