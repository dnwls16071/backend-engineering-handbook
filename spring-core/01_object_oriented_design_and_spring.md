# Object-Oriented Design and Spring

Spring Framework의 IoC 컨테이너는 애플리케이션 객체를 만들고 의존관계를 연결한다. 주문 처리 코드가 할인 정책의 계약에 의존하면, 어떤 정책 인스턴스를 전달할지는 구성 코드가 결정할 수 있다. 이 시리즈의 예제는 **Java 17과 Spring Framework 6.2**를 기준으로 한다. [Spring Framework 6.2 · IoC와 의존관계 주입](https://docs.spring.io/spring-framework/reference/6.2/core/beans/introduction.html)

## 1. 역할과 구현을 분리하는 이유

`DiscountPolicy`가 할인액을 계산하는 계약이라면 고정액 할인과 정률 할인은 그 계약의 구현이다. 주문 서비스는 계약을 통해 값을 받고 주문 금액을 계산한다. 서비스가 구현을 직접 생성하면 정책을 바꿀 때 서비스 코드까지 수정하게 된다. 구현 선택을 외부에서 맡으면 서비스는 주문 처리 흐름을 유지한 채 다른 정책과 협력할 수 있다. [Spring Framework 6.2 · Dependency Injection](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 2. SOLID를 주문 예제에 적용

| 원칙 | 주문 예제에서 확인할 점 |
| --- | --- |
| 단일 책임 원칙(SRP) | 주문 서비스는 주문을 계산하고, 구성 코드는 사용할 할인 정책을 선택한다. |
| 개방-폐쇄 원칙(OCP) | 새 할인 정책을 추가할 때 주문 처리 로직이 유지되도록 확장 지점을 둔다. |
| 리스코프 치환 원칙(LSP) | 고정액·정률 정책 모두 할인액이 0원 이상이고 주문 금액 이하라는 계약을 지킨다. |
| 인터페이스 분리 원칙(ISP) | 할인 계산 인터페이스에는 서비스가 사용하는 계산 연산만 둔다. |
| 의존관계 역전 원칙(DIP) | 주문 처리 코드는 정책의 구체 클래스 대신 할인 계산 계약에 의존한다. |

정책이 인터페이스를 구현해도, 주문 서비스의 본문에 `new FixedDiscountPolicy()`가 있으면 그 서비스는 구체 클래스의 생성에 의존한다. 서비스의 생성자로 정책을 전달하면 결합 지점이 구성 코드로 옮겨진다. [Robert C. Martin · SOLID의 목적](https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html) · [Spring Framework 6.2 · 생성자 주입](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 3. Spring Framework와 Spring Boot

Spring Framework는 컨테이너, AOP, 트랜잭션, 웹 기능 등을 제공한다. Spring Boot는 클래스패스와 설정을 바탕으로 필요한 구성을 자동 적용하고, 애플리케이션을 실행할 수 있는 기본 구성을 제공한다. 도메인 객체를 연결하는 원리는 Boot의 자동 설정을 사용하는 경우에도 같다. [Spring Framework 6.2 · 개요](https://docs.spring.io/spring-framework/reference/6.2/overview.html) · [Spring Boot 3.5 · 자동 설정](https://docs.spring.io/spring-boot/3.5/reference/using/auto-configuration.html)

[02번 문서](02_modeling_orders_and_discount_policies.md)에서 할인 정책의 계약과 주문 처리 흐름을 순수 Java로 구성한다.
