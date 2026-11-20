# Spring Autowiring and Dependency Resolution

자동 주입은 등록된 빈 중에서 의존관계를 만족하는 후보를 찾아 전달한다. 주입할 타입을 계약으로 표현하고, 같은 타입의 구현이 여러 개라면 어느 구현을 어떤 역할에 사용할지 선언한다. [Spring Framework 6.2 · Autowired](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired.html)

## 1. 주입 지점과 선택적 의존성

| 방식 | 특징 |
| --- | --- |
| 생성자 주입 | 필수 의존성을 객체 생성 시점에 받고 `final` 필드로 보관할 수 있다. |
| setter·일반 메서드 주입 | 객체를 생성한 뒤 컨테이너가 메서드를 호출한다. 여러 매개변수를 한 번에 전달할 수 있다. |
| 필드 주입 | 컨테이너가 객체 생성 후 필드를 채운다. 직접 객체를 만들 때는 필요한 입력을 생성자로 확인하기 어렵다. |

관리 빈에 생성자가 하나라면 `@Autowired`를 생략해도 된다. 필수 주입점에 후보가 없으면 빈 생성을 실패시킨다. 선택적 메서드 주입에서 `@Autowired(required = false)`를 지정하면 필요한 인자를 제공할 수 없을 때 메서드 호출을 건너뛴다. `Optional<T>` 또는 `org.springframework.lang.Nullable`을 사용하면 해당 인자의 부재를 명시적으로 다룰 수 있다. [Spring Framework 6.2 · 생성자와 선택적 주입](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired.html)

## 2. 같은 타입의 빈이 여러 개일 때

`@Primary`는 여러 후보 중 단일 값을 주입할 때 우선 후보로 사용한다. `@Qualifier`는 타입이 맞는 후보를 역할이나 지정한 값으로 좁힌다. 필요한 경우 `@Qualifier`를 메타 애노테이션으로 사용해 업무 역할을 표현하는 애노테이션을 만들 수 있다. [Spring Framework 6.2 · Primary](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired-primary.html) · [Spring Framework 6.2 · Qualifier](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired-qualifiers.html)

[02번과 03번의 할인 정책](03_dependency_injection_and_spring_configuration.md)을 같이 등록하는 별도 구성이다. `QuoteComparator`의 첫 번째 정책에는 고정액 할인을, 두 번째 정책에는 기본값인 정률 할인을 전달한다.

```java
public record QuoteComparator(DiscountPolicy fixed, DiscountPolicy preferred) {}
```

```java
@Configuration(proxyBeanMethods = false)
public class PolicySelectionConfig {
    @Bean
    DiscountPolicy fixedDiscountPolicy() {
        return new FixedDiscountPolicy();
    }

    @Bean
    @Primary
    DiscountPolicy percentageDiscountPolicy() {
        return new PercentageDiscountPolicy();
    }

    @Bean
    QuoteComparator quoteComparator(
            @Qualifier("fixedDiscountPolicy") DiscountPolicy fixed,
            DiscountPolicy preferred) {
        return new QuoteComparator(fixed, preferred);
    }
}
```

타입 후보가 여럿이고 별도의 선택 단서가 없다면 주입점 이름과 빈 이름이 일치하는 후보를 찾을 수 있다. Java 생성자나 메서드의 매개변수 이름으로 이 동작을 쓰려면 `-parameters` 옵션으로 컴파일한다. 외부 이름 변경에 영향받지 않게 하려면 의도에 맞는 한정자를 명시할 수 있다. [Spring Framework 6.2 · 주입점 이름과 후보 선택](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired-qualifiers.html)

## 3. 모든 구현을 받는 방법

`List<DiscountPolicy>`를 받으면 타입이 맞는 후보들을 함께 주입한다. 순서가 중요하면 `@Order`나 `Ordered`로 우선순위를 표현한다. `Map<String, DiscountPolicy>`는 키가 빈 이름이고 값이 정책 인스턴스이므로, 실행 시점에 정책 이름을 받아 선택하는 데 활용할 수 있다. 단일 값 주입에 사용하는 `@Primary`는 컬렉션에서 다른 후보를 제외하지 않는다. [Spring Framework 6.2 · 배열, 컬렉션, 맵 주입](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired.html) · [Spring Framework 6.2 · Primary API](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/context/annotation/Primary.html)
