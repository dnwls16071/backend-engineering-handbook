# Using JDK Dynamic Proxies and Class-Based Proxies

프록시는 호출자가 가진 참조와 실제 작업 사이에서 호출을 받아 위임한다. 프록시 패턴은 이 경계에서 접근 제어, 지연 초기화, 호출 기록 같은 처리를 맡길 때 쓴다. JDK 동적 프록시는 런타임에 인터페이스 구현체를 생성한다. Spring AOP는 클래스 자체를 프록시할 때 CGLIB로 하위 클래스를 생성할 수 있다. [프록시 패턴](../design-pattern/09_proxy_pattern.md) · [Oracle · Proxy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html) · [Spring Framework · Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)

## 1. 인터페이스 호출을 한 곳에서 처리하기

`Proxy.newProxyInstance()`에 인터페이스를 볼 수 있는 클래스 로더, 구현할 인터페이스 목록, `InvocationHandler`를 전달한다. 핸들러는 프록시 객체, 호출된 `Method`, 인자를 받는다. 메서드를 타깃에 위임할 때는 타깃을 수신자로 전달한다. 수신자를 프록시로 지정하면 같은 핸들러로 다시 진입한다. [Oracle · Proxy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html) · [Oracle · InvocationHandler](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/InvocationHandler.html)

아래를 `DynamicProxyDemo.java`로 저장한다. `available()`은 프록시 인터페이스의 default 메서드다. `invokeDefault()`로 실행하면 그 안의 `quantity()` 호출도 프록시를 거쳐 별도로 기록된다. 이 예제의 프록시는 `equals()`, `hashCode()`, `toString()`을 객체 동일성 기준으로 처리한다.

```java
import java.io.IOException;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;

public class DynamicProxyDemo {
    public interface StockLookup {
        int quantity(String sku) throws IOException;

        default boolean available(String sku) throws IOException {
            return quantity(sku) > 0;
        }
    }

    public static void main(String[] args) throws IOException {
        StockLookup target = sku -> {
            if (sku.isBlank()) {
                throw new IOException("missing SKU");
            }
            return sku.equals("shoe-01") ? 3 : 0;
        };

        StockLookup lookup = (StockLookup) Proxy.newProxyInstance(
                StockLookup.class.getClassLoader(),
                new Class<?>[] { StockLookup.class },
                (proxy, method, arguments) -> {
                    if (method.getDeclaringClass() == Object.class) {
                        return switch (method.getName()) {
                            case "equals" -> proxy == arguments[0];
                            case "hashCode" -> System.identityHashCode(proxy);
                            case "toString" -> "StockLookup proxy";
                            default -> throw new IllegalStateException(method.toString());
                        };
                    }

                    System.out.println("call " + method.getName());
                    if (method.isDefault()) {
                        return InvocationHandler.invokeDefault(proxy, method, arguments);
                    }
                    try {
                        return method.invoke(target, arguments);
                    } catch (InvocationTargetException failure) {
                        throw failure.getCause();
                    }
                });

        System.out.println(lookup.available("shoe-01"));
        try {
            lookup.quantity("");
        } catch (IOException failure) {
            System.out.println(failure.getMessage());
        }
    }
}
```

```bash
javac DynamicProxyDemo.java
java DynamicProxyDemo
```

```text
call available
call quantity
true
call quantity
missing SKU
```

핸들러가 `InvocationTargetException`을 벗기면 인터페이스의 `throws`에 선언된 `IOException`이 호출자에게 전달된다. 핸들러가 인터페이스에 선언되지 않은 체크 예외를 던지면 프록시 호출은 `UndeclaredThrowableException`으로 감싼다. 검증과 예외 변환을 적용할 때 인터페이스의 계약을 확인한다. [Oracle · InvocationHandler](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/InvocationHandler.html) · [Oracle · UndeclaredThrowableException](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/UndeclaredThrowableException.html)

## 2. 클래스의 가상 메서드를 가로채기

JDK 프록시는 인터페이스 구현 타입으로 사용할 수 있다. 호출자가 구체 클래스의 메서드를 호출해야 한다면 상속 가능한 클래스에 CGLIB 프록시를 적용할 수 있다. 하위 클래스가 재정의할 수 있는 메서드에 어드바이스가 적용된다. `final` 클래스는 상속할 수 없고, `final`과 `private` 메서드는 재정의할 수 없다. 대상이 자기 자신에게 `this`로 호출하면 Spring AOP 프록시를 지나지 않는다. 위 default 메서드 실습은 프록시를 수신자로 지정한 JDK API 예제다. [Spring Framework · Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html) · [Spring AOP 자기 호출](../spring-advanced/12_spring_aop_proxy_limitations_and_self_invocation.md)

Spring Framework 6.2의 `org.springframework:spring-aop`가 클래스패스에 있는 Java 프로젝트에서 아래 코드를 실행한다. `ProxyFactory`에 `setProxyTargetClass(true)`를 지정하고 `MethodInterceptor`로 호출을 기록한다. [Spring ProxyFactory와 Advisors](../spring-advanced/05_spring_proxyfactory_and_advisors.md)

```java
import org.aopalliance.intercept.MethodInterceptor;
import org.springframework.aop.framework.ProxyFactory;

public class ClassProxyDemo {
    public static class StockService {
        public String status() {
            return "available";
        }

        public final String version() {
            return "v1";
        }
    }

    public static void main(String[] args) {
        ProxyFactory factory = new ProxyFactory(new StockService());
        factory.setProxyTargetClass(true);
        factory.addAdvice((MethodInterceptor) call -> {
            System.out.println("call " + call.getMethod().getName());
            return call.proceed();
        });

        StockService service = (StockService) factory.getProxy();
        System.out.println(service.status());
        System.out.println(service.version());
    }
}
```

```text
call status
available
v1
```

`status()`는 프록시의 재정의 지점을 통과한다. `version()` 호출은 동일한 프록시 객체에서 실행되지만 재정의 지점이 없으므로 기록이 생기지 않는다. [Spring Framework · Using ProxyFactory](https://docs.spring.io/spring-framework/reference/6.2/core/aop-api/prog.html)

## 3. Spring Data JPA 리포지토리에서 호출이 향하는 곳

Spring Data는 리포지토리 인터페이스의 메타데이터를 읽고 리포지토리 팩토리로 프록시를 만든다. JPA의 기본 CRUD 메서드는 기본 구현체인 `SimpleJpaRepository`로 이어진다. 사용자가 선언한 쿼리 메서드는 전략에 따라 선언된 쿼리를 찾거나 메서드 이름에서 쿼리를 파생하고, 커스텀 리포지토리 프래그먼트의 메서드는 등록된 프래그먼트가 실행한다. 프록시를 조사할 때는 어떤 인터페이스를 구현했는지와 어떤 호출이 어느 구현에 위임되는지를 함께 본다. [Spring Data · RepositoryFactorySupport](https://docs.spring.io/spring-data/commons/docs/current/api/org/springframework/data/repository/core/support/RepositoryFactorySupport.html) · [Spring Data JPA · Query Methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html) · [Spring Data JPA · Custom Repository Implementations](https://docs.spring.io/spring-data/jpa/reference/repositories/custom-implementations.html)
