# Modeling Orders and Discount Policies

주문은 상품 코드와 할인 전 금액을 받고, 할인액을 계산해 결제 금액을 만든다. 예제의 금액 단위는 원이고, 고정 할인액은 1,000원이다. 각 타입은 같은 패키지의 별도 파일에 둔다.

## 1. 주문 결과와 할인 정책

```java
public record PricedOrder(String sku, int subtotal, int discount) {
    public int total() {
        return subtotal - discount;
    }
}
```

```java
public interface DiscountPolicy {
    int discountFor(int subtotal);
}
```

```java
public class FixedDiscountPolicy implements DiscountPolicy {
    @Override
    public int discountFor(int subtotal) {
        return Math.min(subtotal, 1_000);
    }
}
```

할인 정책에는 0원 이상인 금액을 전달하고, 해당 금액을 넘지 않는 할인액을 기대한다. 이 예에서는 계산에 필요한 값만 정책에 전달한다. 고객 등급을 읽어야 하는 요구가 생기면 고객 조회 계약을 별도 협력 객체로 두고, 저장 방식이나 할인 계산과 분리할 수 있다.

## 2. 순수 Java로 주문 흐름 실행

```java
public class OrderService {
    private final DiscountPolicy discountPolicy = new FixedDiscountPolicy();

    public PricedOrder price(String sku, int subtotal) {
        if (subtotal < 0) {
            throw new IllegalArgumentException("subtotal must be non-negative");
        }
        return new PricedOrder(sku, subtotal, discountPolicy.discountFor(subtotal));
    }
}
```

```java
OrderService service = new OrderService();
PricedOrder order = service.price("BOOK-1", 20_000);
assert order.total() == 19_000;
assert service.price("BOOK-2", 600).total() == 0;
```

위 Java `assert`는 실행 옵션 `-ea`에서 활성화된다. 주문 계산은 컨테이너 없이 확인할 수 있다. 현재 서비스 내부가 고정액 정책을 선택하므로, [03번 문서](03_dependency_injection_and_spring_configuration.md)에서는 정책을 바꾸더라도 주문 로직을 다시 쓰지 않도록 조립 위치를 옮긴다. [Spring Framework 6.2 · POJO와 컨테이너 없는 단위 테스트](https://docs.spring.io/spring-framework/reference/6.2/testing/unit.html)
