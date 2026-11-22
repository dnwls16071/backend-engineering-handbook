# Applying the Dependency Inversion Principle

DIP를 적용할 때는 인터페이스의 존재보다 의존 방향과 소유권을 본다. 상위 업무 규칙이 정의한 환율 포트를 외부 HTTP 어댑터가 구현하는 예로 설명한다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html)

## 1. 업무가 필요로 하는 규약을 안쪽에 둔다

PaymentService는 애플리케이션이 소유하는 ExRateProvider를 참조한다. 어댑터가 이 규약을 구현하고 HTTP 응답을 업무 타입으로 변환한다. 애플리케이션 패키지가 어댑터 구현을 참조하지 않아야 한다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 2. DIP와 주입을 각각 확인한다

DIP는 코드 의존 방향을 다루고 DI는 그 규약을 만족하는 객체를 넣는 방법이다. 인터페이스가 인프라 모델을 그대로 노출하거나 서비스가 외부 구현 이름을 알아야 하면 타입 경계를 다시 확인한다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)
