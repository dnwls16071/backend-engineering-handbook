# Spring Singletons and Configuration Proxies

기본 싱글톤 스코프에서는 컨테이너가 빈 정의 하나에 대해 인스턴스 하나를 공유한다. 클래스가 같아도 빈 정의가 두 개면 인스턴스가 각각 생성될 수 있으며, 별도 컨테이너에는 별도 인스턴스가 존재한다. [Spring Framework 6.2 · 싱글톤 스코프](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html#beans-factory-scopes-singleton)

## 1. 공유되는 서비스에서 상태 다루기

웹 서버의 여러 요청이 같은 서비스 빈을 사용할 수 있다. 예를 들어 현재 요청의 주문 금액을 서비스 필드에 저장하면 다른 요청이 같은 필드를 덮어쓸 수 있다. 주문 금액, 현재 고객, 계산 결과는 지역 변수나 메서드 인자로 전달한다. 공유 캐시처럼 여러 요청이 의도적으로 상태를 함께 사용한다면 그 상태의 동시성 정책을 따로 설계한다.

```java
try (var context = new AnnotationConfigApplicationContext(OrderingConfig.class)) {
    OrderService first = context.getBean(OrderService.class);
    OrderService second = context.getBean(OrderService.class);
    assert first == second;
}
```

위 비교는 [03번 구성](03_dependency_injection_and_spring_configuration.md)에서 실행한다. 같은 객체가 반환된다는 사실은 인스턴스 공유를 확인하며, 객체 코드의 스레드 안전성은 공유 상태를 사용하는 방식에 따라 달라진다.

## 2. @Configuration에서 빈 메서드를 직접 호출할 때

```java
@Configuration
public class FullOrderingConfig {
    @Bean
    DiscountPolicy discountPolicy() {
        return new PercentageDiscountPolicy();
    }

    @Bean
    OrderService orderService() {
        return new OrderService(discountPolicy());
    }
}
```

기본 `@Configuration`으로 등록된 설정 클래스는 런타임 서브클래스로 보강될 수 있다. 위 `orderService()`가 호출하는 `discountPolicy()`는 컨테이너가 가로채며, 해당 빈의 스코프를 따라 관리된 인스턴스를 가져온다. 직접 `new FullOrderingConfig()`로 만든 객체에서는 일반 Java 메서드 호출이 일어난다. [Spring Framework 6.2 · Configuration과 빈 사이의 호출](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/configuration-annotation.html)

## 3. proxyBeanMethods와 메서드 매개변수

`@Configuration(proxyBeanMethods = false)`에서는 빈 메서드끼리 직접 호출해도 컨테이너가 호출을 가로채지 않는다. 위 예에서 메서드를 직접 호출하면 본문의 `new PercentageDiscountPolicy()`가 다시 실행된다. 컨테이너에 등록된 빈 자체는 여전히 지정한 스코프를 따른다.

빈 사이의 의존관계는 `OrderService orderService(DiscountPolicy discountPolicy)`처럼 메서드 매개변수로 받으면 된다. 이 경우 구성 클래스 프록시 여부와 관계없이 컨테이너가 해당 의존 빈을 찾아 전달한다. [Spring Framework 6.2 · Java 설정의 전체 모드와 간소화 모드](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/basic-concepts.html)
