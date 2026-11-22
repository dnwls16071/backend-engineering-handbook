# Connecting Design Principles and Patterns

설계 원칙은 어떤 결합을 줄이려는지 설명하고, 패턴은 그 결합을 바꾸는 구성 방법을 제시한다. 환율 변경을 예로 선택한 경계가 실제 변화 방향과 맞는지 본다. [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 1. 같은 설계에서 원칙과 패턴을 연결한다

| 관점 | 환율 예제의 적용 | 근거 |
| --- | --- | --- |
| 관심사 분리 | 금액 계산, 외부 조회, 객체 조합을 구분한다. | [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) |
| 개방 폐쇄 원칙 | 제공자 추가라는 변화는 기존 계산을 유지하며 구현을 추가할 수 있게 한다. | [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) |
| Strategy와 DI | 제공자 정책을 협력자로 두고 외부에서 구현을 연결한다. | [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) |

## 2. 추상화의 비용도 확인한다

구체적인 교체 이유나 테스트 경계가 있을 때 인터페이스를 추가한다. 역할이 늘어나면 설정과 계약 검증 비용도 생기므로 예측할 수 있는 변화부터 적용한다. [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)
