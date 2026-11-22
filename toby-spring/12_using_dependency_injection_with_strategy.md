# Using Dependency Injection with Strategy

고정 환율과 외부 환율 조회를 전략으로 둘 수 있다. 결제 준비는 같은 ExRateProvider 계약을 사용하고, 어떤 전략이 연결되는지는 객체 조립에서 결정한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 1. 알고리즘과 선택을 나눈다

외부 환율 조회는 네트워크를 쓰고, 고정 제공자는 테스트나 예시에 정해진 값을 반환한다. 같은 서비스 호출에서 전략만 교체했을 때 계산은 기계적으로 같은 규칙을 적용해야 한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)

## 2. 선택 시점을 명확히 한다

애플리케이션 전체에서 정한 전략은 생성자에 연결한다. 호출마다 달라지는 정책이면 메서드 인수나 별도의 정책 선택기에서 결정하는 안을 비교한다. 각 구현이 계약을 지키는지 공통 입력으로 검사한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf)
