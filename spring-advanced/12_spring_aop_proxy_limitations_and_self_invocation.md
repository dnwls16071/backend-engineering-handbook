# Spring AOP Proxy Limitations and Self-Invocation

프록시 기반 AOP에서 어드바이스가 실행되려면 대상 메서드의 호출이 프록시를 통과해야 한다. 프록시가 적용된 빈의 외부 메서드를 호출하더라도, 대상 객체가 내부에서 자기 메서드를 다시 부르면 그 내부 호출은 `this`를 사용한다. [Spring Framework 6.2 · 프록시와 자기 호출](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)

## 1. 내부 호출을 프록시 경계 밖으로 옮기기

```java
public class QuoteFacade {
    private final PriceLookup lookup;

    public QuoteFacade(PriceLookup lookup) {
        this.lookup = lookup;
    }

    public int checkoutPrice(String sku) {
        return lookup.quote(sku);
    }
}
```

워크플로와 조회를 별도 빈으로 구성하면 `QuoteFacade`가 주입받은 `PriceLookup` 프록시를 통해 호출할 수 있다. 기존 클래스 안의 두 작업이 분리하기 어려운 경우 `ObjectProvider`나 자기 참조 주입으로 프록시를 얻는 방식도 있다. 자기 참조 방식은 빈 생성 순서와 의존관계를 복잡하게 하므로, 먼저 역할을 나눌 수 있는지 확인한다. [Spring Framework 6.2 · 자기 호출 처리 방식](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html) · [Spring Framework 6.2 · Self Injection](https://docs.spring.io/spring-framework/reference/6.2/core/beans/annotation-config/autowired.html)

## 2. 타입과 가로채기 한계

| 항목 | 확인할 점 |
| --- | --- |
| JDK 동적 프록시 | 프록시는 대상 인터페이스를 구현한다. 주입점도 프록시가 제공하는 인터페이스 타입으로 선언한다. |
| CGLIB 프록시 | 대상의 하위 클래스다. `final` 클래스와 오버라이드할 수 없는 메서드는 제약을 받는다. |
| 클래스 프록시의 생성자 | Spring은 일반적으로 Objenesis를 사용해 프록시를 생성하며, JVM에서 생성자 우회가 허용되지 않으면 동작이 달라질 수 있다. |
| Spring Boot 자동 설정 | 기본 프록시 유형은 클래스 기반이다. `spring.aop.proxy-target-class`로 방식을 설정할 수 있다. |

클래스 프록시를 선택해도 일반적인 Spring AOP의 자기 호출은 같은 대상 객체 안에서 실행된다. `@Transactional`을 사용하는 메서드도 프록시 모드에서는 같은 호출 경계의 영향을 받는다. [Spring Framework 6.2 · 프록시 생성 제약](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html) · [Spring Boot 3.5 · AOP 자동 설정](https://docs.spring.io/spring-boot/3.5/reference/features/aop.html) · [Spring Framework 6.2 · Transactional 애노테이션](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html)

## 3. 어드바이스가 실행되지 않을 때

1. 컨테이너에서 받은 빈을 호출하는지 확인한다. `AopUtils.isAopProxy()`는 프록시 여부를 확인하는 데 쓸 수 있다. [Spring Framework 6.2 · AopUtils API](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/aop/support/AopUtils.html)
2. 호출 지점이 대상 객체 내부인지, 메서드가 현재 프록시 방식에서 가로챌 수 있는지 확인한다.
3. 메서드·패키지·애노테이션이 포인트컷에 맞는지 실제 빈 호출로 검증한다.
