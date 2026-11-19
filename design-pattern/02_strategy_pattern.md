# Strategy Pattern

전략은 같은 역할을 수행하는 여러 알고리즘을 공통 계약으로 제공하는 행동 패턴이다. 업무 흐름을 가진 컨텍스트는 선택한 알고리즘에 계산을 위임하고, 구성 코드나 호출자가 사용할 전략을 결정한다. [GoF의 Strategy](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 어떤 문제를 푸는가

배송 견적을 만드는 흐름은 상품 합계에 배송비를 더하는 것으로 일정하다. 배송비는 기본 정책이나 무료 배송 정책에 따라 달라진다. 배송비 계산을 `ShippingFee`로 분리하면 두 정책을 같은 방식으로 호출하고 정책별 테스트를 별도로 작성할 수 있다.

## Java 17 예제

```java
public class StrategyExample {
    @FunctionalInterface
    interface ShippingFee {
        int fromSubtotal(int subtotalWon);
    }

    record Checkout(ShippingFee shippingFee) {
        int total(int subtotalWon) {
            return Math.addExact(subtotalWon, shippingFee.fromSubtotal(subtotalWon));
        }
    }

    public static void main(String[] args) {
        ShippingFee flatRate = subtotal -> 3_000;
        ShippingFee freeFromFiftyThousand = subtotal ->
                subtotal >= 50_000 ? 0 : flatRate.fromSubtotal(subtotal);

        int standard = new Checkout(flatRate).total(50_000);
        int promotion = new Checkout(freeFromFiftyThousand).total(50_000);
        if (standard != 53_000 || promotion != 50_000) {
            throw new AssertionError(standard + ", " + promotion);
        }
        System.out.println(standard + ", " + promotion);
    }
}
```

실행 결과는 `53000, 50000`이다. 두 견적은 같은 합산 과정을 사용하고 선택한 정책에 따라 다른 배송비를 반환한다.

## 적용할 때 볼 점

- 어떤 알고리즘을 선택할지는 구성이나 호출부의 결정이다. 새 전략을 추가하면 선택 규칙과 전략별 계약을 함께 확인한다.
- 메서드 하나로 표현되는 전략은 람다로 둘 수 있다. 각 전략이 설정이나 협력 객체를 관리한다면 이름 있는 타입이 해당 책임을 설명하기 쉽다.
- 전략은 정책 선택을 표현한다. 상태 패턴에서는 객체가 진행 단계에 따라 다른 동작을 하고, 상태 전이도 모델에 포함된다. 템플릿 메서드는 상위 클래스가 정한 절차의 일부 단계를 하위 클래스가 구현한다. [State Pattern](05_state_pattern.md) · [Template Method Pattern](03_template_method_pattern.md)
