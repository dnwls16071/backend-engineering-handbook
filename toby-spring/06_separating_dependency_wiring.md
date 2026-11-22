# Separating Dependency Wiring

PaymentService가 환율 제공자를 쓰는 일과 실행에 어떤 구현을 연결할지 정하는 일을 나눈다. 생성자에서 필요한 협력자를 받으면 사용 조건을 객체 생성 시점에 확인할 수 있다. [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 1. 구성 단계에서 객체를 연결한다

진입점이 WebApiExRateProvider를 만든 뒤 PaymentService의 생성자에 전달한다. 서비스의 필드는 ExRateProvider 계약을 사용한다. 필수 협력자를 생성자 인수로 드러내고, 테스트에서는 같은 자리로 대역을 전달한다. [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)

## 2. 코드 참조와 실행 연결을 따로 본다

업무 코드가 인터페이스를 참조하고 실행 시 제공자 구현을 사용한다. 구성 코드는 구현을 알고 선택하며, 주소나 시크릿은 환경 설정에서 제공받도록 설계한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)
