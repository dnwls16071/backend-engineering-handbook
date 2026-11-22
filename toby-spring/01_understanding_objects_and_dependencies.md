# Understanding Objects and Dependencies

PaymentService가 환율을 얻어 결제 금액을 준비하는 작은 예로 시작한다. 이 객체는 환율 조회 기능을 호출하는 협력자에게 의존한다. 의존관계는 소스 코드가 참조하는 타입과 실행 중 사용하는 실제 객체를 나눠 볼 수 있다. [Spring 6.2 IoC](https://docs.spring.io/spring-framework/reference/6.2/core/beans/introduction.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 1. 호출하는 책임과 구현이 바뀌는 위치를 찾는다

서비스가 내부에서 웹 환율 객체를 생성하면 네트워크 구현과 객체 생성 시점도 서비스에 들어온다. 환율만 필요한 코드에는 필요한 협력자를 전달하고, HTTP 호출을 바꿀 때나 테스트할 때 객체 조합을 교체할 수 있게 한다. [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 2. 주제별 읽기

| 문서 번호 | 학습 흐름 | 근거 |
| --- | --- | --- |
| 01~14 | [의존관계 주입](09_injecting_dependencies_with_the_spring_container.md), [싱글톤 레지스트리](11_understanding_the_spring_singleton_registry.md), [DIP](14_applying_the_dependency_inversion_principle.md) | [Spring 6.2 IoC](https://docs.spring.io/spring-framework/reference/6.2/core/beans/introduction.html) · [Spring 6.2 Bean Scopes](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) |
| 15~23 | [자동화 테스트](15_automating_repeatable_tests.md), [Clock으로 시간 테스트](22_testing_time_with_clock.md) | [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) |
| 24~34 | [환율 조회 리팩터링](26_refactoring_web_api_exchange_rate_provider.md), [템플릿 추출](32_extracting_api_template.md) | [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) |
| 35~38 | [예외 처리](35_handling_exceptions_at_boundaries.md), [데이터 접근 예외 추상화](38_translating_data_access_exceptions.md) | [Java 21 JLS Exceptions](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html) · [Spring 6.2 DAO Support](https://docs.spring.io/spring-framework/reference/6.2/data-access/dao.html) |
| 39~47 | [서비스 계층](39_defining_a_service_layer.md), [트랜잭션 추상화](43_abstracting_transaction_management.md), [선언적 트랜잭션 AOP](47_using_transactional_with_spring_aop.md) | [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html) · [Spring 6.2 @Transactional](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html) |
