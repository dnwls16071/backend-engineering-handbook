# Spring Component Scanning

컴포넌트 스캔은 패키지에서 빈 후보를 발견해 정의를 등록한다. 등록된 빈의 의존관계는 생성자나 다른 주입 지점에서 별도로 해결된다. [Spring Framework 6.2 · 클래스패스 스캔](https://docs.spring.io/spring-framework/reference/6.2/core/beans/classpath-scanning.html)

## 1. 스캔 범위와 후보

```java
@Configuration(proxyBeanMethods = false)
@ComponentScan(basePackages = "example.order.components")
public class ScanConfig {}
```

`basePackages`를 지정하지 않으면 구성 클래스의 패키지부터 탐색한다. 대상 패키지에 둔 기준 클래스를 `basePackageClasses`로 넘기면 문자열 없이 시작 위치를 지정할 수 있다. Spring Boot의 `@SpringBootApplication`도 컴포넌트 스캔을 포함하므로 애플리케이션 클래스를 도메인 패키지의 상위에 두는 구성이 일반적이다. [Spring Framework 6.2 · ComponentScan API](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/context/annotation/ComponentScan.html) · [Spring Boot 3.5 · SpringBootApplication](https://docs.spring.io/spring-boot/3.5/reference/using/using-the-springbootapplication-annotation.html)

기본 후보에는 `@Component`, `@Service`, `@Repository`, `@Controller`처럼 `@Component`를 포함하는 애노테이션으로 표시된 클래스가 있다. `@Configuration`도 후보에 포함된다. [02번의 고정 할인 정책](02_modeling_orders_and_discount_policies.md)에 `@Component`를 붙여 지정한 범위에 두면, 예를 들어 다음 객체의 생성자로 주입할 수 있다. [Spring Framework 6.2 · 컴포넌트 애노테이션과 자동 탐지](https://docs.spring.io/spring-framework/reference/6.2/core/beans/classpath-scanning.html)

```java
@Service
public class ScannedOrderFacade {
    private final DiscountPolicy discountPolicy;

    public ScannedOrderFacade(DiscountPolicy discountPolicy) {
        this.discountPolicy = discountPolicy;
    }

    public int discountFor(int subtotal) {
        return discountPolicy.discountFor(subtotal);
    }
}
```

[03번의 명시적 Java 설정](03_dependency_injection_and_spring_configuration.md)을 별도 패키지에 두면 이 스캔 예제에 다른 `DiscountPolicy`가 함께 등록되는 것을 피할 수 있다.

## 2. 필터와 중복 이름

| 옵션 | 사용 목적 |
| --- | --- |
| `includeFilters` | 특정 애노테이션이나 타입 등으로 후보를 추가한다. |
| `excludeFilters` | 스캔 범위 안의 테스트 설정이나 별도로 조립할 타입을 제외한다. |
| `useDefaultFilters = false` | 기본 후보 필터를 끄고 명시한 포함 규칙으로 탐색한다. |

빈 이름을 생략하면 기본 이름 생성기가 보통 짧은 클래스명의 첫 글자를 소문자로 바꾼다. 다른 패키지의 두 컴포넌트가 같은 이름으로 탐지되면 빈 이름이 충돌할 수 있다. 명시적 이름이나 이름 생성 정책으로 충돌을 해결한다. 자동 등록과 수동 등록이 겹칠 때는 빈 정의 덮어쓰기 설정과 등록 경로를 함께 검토한다. [Spring Framework 6.2 · 스캔 필터와 컴포넌트 이름](https://docs.spring.io/spring-framework/reference/6.2/core/beans/classpath-scanning.html) · [Spring Boot 3.5 · 빈 정의 덮어쓰기 설정](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html#application-properties.core.spring.main.allow-bean-definition-overriding)
