# AspectJ Annotations in Spring AOP

`@Aspect`와 어드바이스 애노테이션은 적용 조건과 실행할 로직을 함께 선언하는 방법이다. Spring은 등록된 애스펙트를 읽고 적합한 빈을 프록시로 감싼다. Java 설정에서는 `@EnableAspectJAutoProxy`를 사용할 수 있으며, 실행 클래스패스에 AspectJ Weaver 라이브러리가 필요하다. [Spring Framework 6.2 · @AspectJ 지원 활성화](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/aspectj-support.html)

## 1. 조회에 측정 어드바이스 연결

```java
@Aspect
public class QuoteTimingAspect {
    @Around("execution(* example.pricing..*.quote(..))")
    public Object measure(ProceedingJoinPoint joinPoint) throws Throwable {
        long started = System.nanoTime();
        try {
            return joinPoint.proceed();
        } finally {
            System.getLogger("pricing").log(System.Logger.Level.DEBUG,
                "{0} took {1} ns", joinPoint.getSignature().toShortString(),
                System.nanoTime() - started);
        }
    }
}
```

```java
@Configuration(proxyBeanMethods = false)
@EnableAspectJAutoProxy
public class PricingAspectConfig {
    @Bean
    PriceLookup priceLookup() {
        return new FixedPriceLookup();
    }

    @Bean
    QuoteTimingAspect quoteTimingAspect() {
        return new QuoteTimingAspect();
    }
}
```

`PriceLookup`과 구현은 `example.pricing` 패키지에 둔다. `@Aspect`는 애스펙트를 표시하므로, 예제처럼 `@Bean`으로 등록하거나 스캔 대상이 되도록 `@Component`를 함께 붙인다. `@Around`가 `proceed()`의 반환값을 돌려주어 원래 조회 계약을 유지한다. [Spring Framework 6.2 · 애스펙트 선언](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/at-aspectj.html) · [Spring Framework 6.2 · Around Advice](https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/advice.html)

## 2. 빈 조회부터 실제 호출까지

컨테이너에서 `PriceLookup`을 받은 호출자가 `quote()`를 호출하면, 프록시가 적용할 어드바이스를 실행한다. 애스펙트 선언을 읽는 작업과 프록시에서 메서드를 가로채는 작업은 실행 과정의 서로 다른 단계다. 테스트는 `new FixedPriceLookup()`의 호출과 컨테이너에서 받은 빈의 호출을 각각 확인할 수 있다. [Spring Framework 6.2 · Spring AOP 프록시 호출 구조](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)
