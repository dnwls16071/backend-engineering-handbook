# Spring AOP Advice and Ordering

애스펙트를 구현할 때는 실행 시점에 맞는 어드바이스를 선택하고, 여러 어드바이스가 하나의 호출을 감쌀 때의 순서를 정한다. 아래 코드는 [07번의 애스펙트 등록 방식](07_aspectj_annotations_in_spring_aop.md)을 사용한다. [Spring Framework 6.2 · 어드바이스 선언](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/advice.html)

## 1. 실행 시점에 따른 어드바이스

| 애노테이션 | 동작 |
| --- | --- |
| `@Before` | 대상 메서드 실행 전 호출된다. |
| `@AfterReturning` | 대상이 정상 반환했을 때 호출된다. 반환값 일부를 바인딩할 수 있다. |
| `@AfterThrowing` | 대상 호출이 대응하는 예외를 던졌을 때 호출된다. |
| `@After` | 정상 반환과 예외에 관계없이 종료 시 실행된다. |
| `@Around` | 실행 전후를 감싸며, `proceed()` 여부와 반환값을 직접 제어한다. |

실행 전 기록만 필요하면 `@Before`로 표현할 수 있다. `@Around`에서는 `proceed()`를 호출하지 않으면 원래 메서드가 실행되지 않으므로, 조회의 반환값과 예외가 호출자에게 전달되는지 확인한다. [Spring Framework 6.2 · 어드바이스 종류](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/advice.html)

## 2. 이름을 붙인 포인트컷 공유

```java
@Aspect
@Order(10)
public class QuoteAuditAspect {
    @Pointcut("execution(* example.pricing..*.quote(..))")
    public void quoteOperation() {}

    @Before("quoteOperation()")
    public void started() {
        System.getLogger("pricing").log(System.Logger.Level.DEBUG, "quote started");
    }

    @AfterThrowing(pointcut = "quoteOperation()", throwing = "failure", argNames = "failure")
    public void failed(RuntimeException failure) {
        System.getLogger("pricing").log(System.Logger.Level.WARNING,
            "quote failed: {0}", failure.getClass().getSimpleName());
    }
}
```

다른 애스펙트에서는 접근 가능한 포인트컷의 클래스와 메서드 이름을 사용해 조건을 공유할 수 있다. [Spring Framework 6.2 · 명명된 포인트컷](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/pointcuts.html)

## 3. 같은 호출을 여러 애스펙트가 감쌀 때

작은 `@Order` 값이 높은 우선순위를 뜻한다. 우선순위가 높은 어드바이스는 호출에 진입할 때 먼저 실행되고, 호출에서 돌아올 때는 나중에 실행된다. 시간 측정과 트랜잭션처럼 바깥·안쪽 관계가 중요한 동작은 별도의 애스펙트로 두고 순서를 명시한다. 같은 애스펙트 안에 같은 종류의 어드바이스가 여러 개라면 소스 코드의 메서드 순서에 의존하지 않는다. [Spring Framework 6.2 · 어드바이스 순서](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/advice.html#aop-ataspectj-advice-ordering)
