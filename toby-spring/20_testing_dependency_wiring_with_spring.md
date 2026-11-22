# Testing Dependency Wiring with Spring

업무 계산은 직접 생성해 빠르게 확인하고, 컨테이너가 선택하는 빈과 프록시가 중요한 경우 테스트용 Spring 구성을 로드한다. [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Spring 6.2 SpringJUnitConfig](https://docs.spring.io/spring-framework/reference/6.2/testing/annotations/integration-junit-jupiter.html)

## 1. 검증할 구성만 등록한다

JUnit Jupiter에서는 @SpringJUnitConfig(TestConfig.class)로 필요한 컨텍스트를 지정할 수 있다. 테스트 구성은 같은 환율 포트에 테스트 대역을 연결하고, 실제 구성을 검사하는 테스트는 기대하는 빈과 동작을 확인한다. [Spring 6.2 SpringJUnitConfig](https://docs.spring.io/spring-framework/reference/6.2/testing/annotations/integration-junit-jupiter.html) · [Spring 6.2 AnnotationConfigApplicationContext](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/instantiating-container.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 2. 설정 문제와 계산 오류를 구분한다

타입 후보가 모호하거나 빈 등록이 빠진 경우에는 컨텍스트 구성 검사에서 찾는다. 테스트 환경의 대역이 프로덕션 설정 문제를 가리지 않도록 업무 테스트와 실제 연결 확인을 구분한다. [Spring 6.2 SpringJUnitConfig](https://docs.spring.io/spring-framework/reference/6.2/testing/annotations/integration-junit-jupiter.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)
