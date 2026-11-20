# Proxy and Decorator Patterns

프록시와 데코레이터는 호출자와 실제 구현 사이에서 같은 인터페이스를 제공할 수 있다. 프록시는 호출을 제어하고, 데코레이터는 기존 계약을 유지하면서 호출 전후의 동작이나 결과를 보강한다. [Proxy Pattern](../design-pattern/09_proxy_pattern.md) · [Decorator Pattern](../design-pattern/16_decorator_pattern.md)

## 1. 가격 조회 계약과 실제 구현

```java
public interface PriceLookup {
    int quote(String sku);
}
```

```java
public class FixedPriceLookup implements PriceLookup {
    @Override
    public int quote(String sku) {
        if (!"BOOK-1".equals(sku)) {
            throw new IllegalArgumentException("unknown SKU");
        }
        return 20_000;
    }
}
```

## 2. 조회 횟수를 줄이는 캐시 프록시

```java
public class CachingPriceLookup implements PriceLookup {
    private final PriceLookup delegate;
    private final ConcurrentMap<String, Integer> prices = new ConcurrentHashMap<>();

    public CachingPriceLookup(PriceLookup delegate) {
        this.delegate = delegate;
    }

    @Override
    public int quote(String sku) {
        return prices.computeIfAbsent(sku, delegate::quote);
    }
}
```

같은 상품의 조회 결과가 있으면 대상 호출을 생략한다. 캐시 키에는 결과에 영향을 주는 데이터가 포함돼야 한다. 변경 가능한 가격에는 만료나 무효화 규칙도 필요하다. 위 예제는 고정 가격을 가정한다. [Java 17 · ConcurrentHashMap](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html)

## 3. 할인 동작을 추가하는 데코레이터

```java
public class DiscountedPriceLookup implements PriceLookup {
    private final PriceLookup delegate;

    public DiscountedPriceLookup(PriceLookup delegate) {
        this.delegate = delegate;
    }

    @Override
    public int quote(String sku) {
        int listPrice = delegate.quote(sku);
        return listPrice - listPrice / 10;
    }
}
```

`PriceLookup lookup = new DiscountedPriceLookup(new FixedPriceLookup())`로 조립하면 상품 가격 20,000원에 10% 할인을 적용한다. 조립 단계에서 어떤 객체를 감쌀지 결정하고, 호출부는 `PriceLookup`을 유지한다.

인터페이스 없는 타입을 같은 타입으로 전달해야 할 때는 하위 클래스 방식도 고려할 수 있다. 상속과 오버라이드 제약을 받으므로 대상 클래스와 메서드가 열려 있는지 확인한다. 여러 타입에 같은 로깅을 붙일 때 수동 래퍼를 계속 작성하는 문제는 [04번 동적 프록시](04_jdk_dynamic_proxies_and_cglib.md)에서 이어진다. [Spring Framework 6.2 · 인터페이스 프록시와 클래스 프록시](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)
