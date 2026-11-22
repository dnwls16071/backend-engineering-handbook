# Testing Transaction Boundaries

트랜잭션 테스트는 정상 완료 시 실제로 저장이 확정되고, 중간 실패 시 일부 변경만 남는 문제를 막는지 확인한다. 테스트 프레임워크가 만드는 범위와 서비스가 만드는 범위를 구분한다. [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html)

## 1. 일부 변경 뒤 실패를 주입한다

첫 번째 저장 직후 실패하도록 실행하고 별도 조회로 두 작업이 남지 않았는지 확인한다. JPA의 제약 위반은 필요하면 flush를 호출해 관측하고, 테스트의 자동 롤백만으로 서비스 커밋 동작을 판단하지 않는다. [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

## 2. 커밋 결과는 완료된 경계 밖에서 읽는다

실제 커밋을 읽어야 하면 외부 테스트 트랜잭션을 두지 않거나 TestTransaction으로 종료를 제어하는 실행을 준비한다. 커밋 테스트의 데이터는 별도 정리하고, 컨텍스트 바인딩이 필요한 검증을 다른 스레드에 넘길 때는 경계를 다시 확인한다. [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring 6.2 Resource Synchronization](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/tx-resource-synchronization.html)
