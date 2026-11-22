# Separating Classes by Responsibility

결제 준비와 환율 조회를 서로 협력하는 클래스로 나눈다. 분리 후 각 객체가 어떤 값과 규칙을 책임지는지 이름으로 확인한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)

## 1. 클래스가 맡는 일을 명시한다

PaymentService는 환율을 요청한 뒤 환산 금액을 구성하고, WebApiExRateProvider는 HTTP 요청과 응답 해석을 담당한다. 업무 서비스가 네트워크 경로를 수정할 필요가 없는지를 첫 검증으로 삼는다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)

## 2. 생성 위치도 확인한다

클래스를 나눴어도 서비스가 직접 WebApiExRateProvider를 만들면 구현 선택은 서비스에 남아 있다. 다음 단계에서 생성 코드를 밖으로 이동할 수 있도록 필요한 협력자를 매개변수로 드러낸다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)
