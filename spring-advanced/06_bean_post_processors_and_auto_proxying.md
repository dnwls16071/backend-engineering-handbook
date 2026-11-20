# Bean Post-Processors and Auto-Proxying

`BeanPostProcessor`는 컨테이너가 생성한 객체에 초기화 전후 동작을 적용한다. 후처리 메서드가 프록시를 반환하면 이후 조회나 주입에서 그 프록시가 사용될 수 있다. 빈 생성에 필요한 메타데이터를 바꾸는 작업은 `BeanFactoryPostProcessor`가 담당한다. [Spring Framework 6.2 · 컨테이너 확장 지점](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-extension.html)

## 1. 선택한 빈을 프록시로 바꾸기

```java
@Configuration(proxyBeanMethods = false)
public class PricingPostProcessorConfig {
    @Bean
    PriceLookup priceLookup() {
        return new FixedPriceLookup();
    }

    @Bean
    static BeanPostProcessor pricingPostProcessor() {
        return new BeanPostProcessor() {
            @Override
            public Object postProcessAfterInitialization(Object bean, String beanName) {
                if (!"priceLookup".equals(beanName) || !(bean instanceof PriceLookup)) {
                    return bean;
                }

                ProxyFactory factory = new ProxyFactory(bean);
                factory.addAdvice((MethodInterceptor) call -> {
                    System.getLogger("pricing").log(System.Logger.Level.DEBUG,
                        "method: {0}", call.getMethod().getName());
                    return call.proceed();
                });
                return factory.getProxy();
            }
        };
    }
}
```

예제는 대상 이름과 타입을 모두 확인한다. 후처리기는 일반 싱글톤보다 이른 단계에 등록되므로 `static @Bean`으로 선언하고 일반 애플리케이션 빈을 의존성으로 받지 않는다. 이 구성은 후처리기 등록 때문에 설정 클래스나 그 협력 객체가 먼저 생성되는 일을 줄인다. [Spring Framework 6.2 · BeanPostProcessor 등록](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-extension.html)

## 2. 어드바이저를 찾는 자동 프록시 생성기

`DefaultAdvisorAutoProxyCreator`는 등록된 어드바이저의 포인트컷을 평가해 적용할 빈을 결정한다. 같은 빈에 맞는 어드바이저가 여러 개면 적합한 어드바이스를 하나의 프록시 체인에 구성할 수 있다. 인자에 의존하는 동적 조건은 호출 때 다시 확인할 수 있다. [Spring Framework 6.2 · 자동 프록시 생성](https://docs.spring.io/spring-framework/reference/6.2/core/aop-api/autoproxy.html)

예제처럼 직접 감싸는 후처리기와 자동 프록시 생성을 같은 대상에 동시에 적용하면 호출 경로에 여러 프록시가 생길 수 있다. 적용 방식을 정한 뒤 컨테이너에서 조회한 객체의 타입과 호출 순서를 검증한다.
