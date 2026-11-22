# Persisting Orders with JPA

Order 저장 어댑터는 영속성 컨텍스트와 트랜잭션을 사용해 주문을 기록한다. 엔터티가 관리 상태가 되는 시점과 INSERT가 실행되는 시점을 구분한다. [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Spring 6.2 JPA](https://docs.spring.io/spring-framework/reference/6.2/data-access/orm/jpa.html)

## 1. 새 엔터티와 분리된 엔터티의 처리 차이

새 엔터티는 persist로 관리 상태에 둔다. merge의 경우 전달 객체의 상태가 관리 인스턴스에 복사되거나 관리 인스턴스가 만들어지며, 이후 변경은 반환된 관리 인스턴스를 대상으로 다룬다. [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

## 2. flush와 커밋을 각각 확인한다

flush는 영속 상태를 DB에 동기화하며 커밋은 트랜잭션 결과를 확정한다. INSERT의 실제 시점은 키 생성 방식이나 flush 조건에 따라 달라질 수 있다. 저장 결과를 재조회할 때는 같은 영속성 컨텍스트의 이전 객체만 확인하는 실수를 피한다. [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
