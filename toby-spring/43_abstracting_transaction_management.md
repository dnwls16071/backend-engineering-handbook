# Abstracting Transaction Management

트랜잭션 경계는 업무의 원자적 완료 단위를 나타낸다. 트랜잭션을 실행하는 세부 기술은 데이터 접근 전략과 함께 구성할 수 있다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html)

## 1. 트랜잭션 전략과 사용 코드를 구분한다

Spring의 PlatformTransactionManager는 시작·커밋·롤백을 공통 계약으로 표현한다. JDBC 또는 JPA에 맞는 구현을 구성하고, 서비스가 직접 상태를 조작하기보다 TransactionTemplate 콜백을 사용하는 안을 비교한다. [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html) · [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html) · [Spring 6.2 JpaTransactionManager](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/orm/jpa/JpaTransactionManager.html)

## 2. 정상 반환과 실패 경로를 검증한다

콜백의 여러 변경이 한 단위로 커밋되는지 확인한다. 콜백에서 복구 불가능한 오류를 처리할 때는 롤백 정책과 반환 계약을 함께 맞춘다. 프레임워크로부터 더 분리해야 하는 영역은 업무 트랜잭션 경계를 포트나 데코레이터로 옮길 수 있다. [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html) · [Spring 6.2 Rollback](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/rolling-back.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)
