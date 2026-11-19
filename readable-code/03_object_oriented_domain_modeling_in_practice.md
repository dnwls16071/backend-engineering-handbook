# Object-Oriented Domain Modeling in Practice

[객체 지향 설계와 SOLID](02_object_oriented_design_and_solid_principles.md)에서 다룬 책임과 협력을 주문 견적에 적용한다. 견적을 만들려면 주문 항목의 소계를 계산하고, 수령 방식과 배송 정책을 적용해 최종 금액을 구해야 한다. 합계 계산, 단위, 유효성 검사에 등장하는 업무 개념을 각각 알맞은 타입과 연산으로 표현한다.

## 1. 상속과 조합 고르기

상속을 고려할 때는 하위 타입을 기존 상위 타입의 자리에 넣어도 호출 계약이 성립하는지 확인한다. 클래스 상속으로 구현을 공유하면 부모의 초기화 방식이나 재정의 가능한 메서드의 호출 순서도 자식의 동작에 영향을 줄 수 있다.

조합은 객체가 필요한 협력 객체를 가지고 그 책임을 위임하는 방식이다. 예를 들어 무료 배송 정책은 기준 금액을 판단하고, 기준 미만인 주문의 배송비 계산은 기본 배송 정책에 위임한다. 기본 정책을 교체해도 무료 배송 기준을 판단하는 코드는 재사용할 수 있다. [Martin Fowler의 Replace Superclass with Delegate](https://refactoring.com/catalog/replaceSuperclassWithDelegate.html)

## 2. 값 객체와 일급 컬렉션으로 규칙 표현하기

**값 객체**는 값으로 동등성을 판단한다. 원 단위 금액을 뜻하는 `Won`은 0 이상이라는 전제를 생성 시 확인하고, 더하기와 수량 곱셈의 결과를 새 값으로 반환한다. Java의 `record`는 구성 요소로 동등성을 비교한다. 구성 요소가 변경 가능한 객체를 참조한다면 그 객체의 변경 가능성도 별도로 다뤄야 한다. [Martin Fowler의 Value Object](https://martinfowler.com/bliki/ValueObject.html) · [Java 레코드](https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.10)

**일급 컬렉션**은 컬렉션의 업무 의미와 규칙을 한 타입에 모은다. `OrderLines`는 견적에 항목이 하나 이상 있어야 한다는 규칙과 소계 계산을 담당한다. `List.copyOf`로 입력 목록의 구조를 복사해 호출자가 원본 목록에 항목을 추가하거나 지워도 견적에 사용할 항목은 유지된다. 내부 요소인 `OrderLine`도 변경 불가능한 값으로 구성한다. [Java List.copyOf](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/List.html#copyOf(java.util.Collection))

## 3. Enum과 다형성을 함께 사용하기

Enum은 유한한 선택지를 타입으로 표현한다. 수령 방식이 매장 수령과 택배 배송 두 가지라면 `FulfillmentMethod`에 정의할 수 있다. 아래 예제는 수령 방식에 따라 배송비 적용 여부를 결정하고, 실제 배송비 계산은 `ShippingPolicy`에 위임한다. 정책의 구체 구현이 바뀌어도 견적을 만드는 쪽은 같은 연산을 요청한다. 외부 시스템이 별도 상태 코드로 값을 주고받는 경우에는 입출력 경계에서 그 코드를 열거형 값에 매핑한다. [Java 열거형](https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.9) · [Java의 런타임 메서드 선택](https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.12.4.4)

```java
import java.util.List;
import java.util.Objects;

record Won(long amount) {
    static final Won ZERO = new Won(0);

    Won {
        if (amount < 0) {
            throw new IllegalArgumentException("Amount must be non-negative");
        }
    }

    Won plus(Won other) {
        return new Won(Math.addExact(amount, other.amount()));
    }

    Won times(int quantity) {
        return new Won(Math.multiplyExact(amount, quantity));
    }

    boolean isAtLeast(Won threshold) {
        return amount >= threshold.amount();
    }
}

record OrderLine(Won unitPrice, int quantity) {
    OrderLine {
        Objects.requireNonNull(unitPrice, "unitPrice");
        if (quantity <= 0) {
            throw new IllegalArgumentException("Quantity must be positive");
        }
    }

    Won subtotal() {
        return unitPrice.times(quantity);
    }
}

final class OrderLines {
    private final List<OrderLine> lines;

    OrderLines(List<OrderLine> lines) {
        this.lines = List.copyOf(lines);
        if (this.lines.isEmpty()) {
            throw new IllegalArgumentException("An order needs at least one line");
        }
    }

    Won subtotal() {
        Won total = Won.ZERO;
        for (OrderLine line : lines) {
            total = total.plus(line.subtotal());
        }
        return total;
    }
}

enum FulfillmentMethod {
    STORE_PICKUP, DELIVERY
}

interface ShippingPolicy {
    Won feeFor(Won subtotal);
}

record FlatRateShipping(Won fee) implements ShippingPolicy {
    FlatRateShipping {
        Objects.requireNonNull(fee, "fee");
    }

    @Override
    public Won feeFor(Won subtotal) {
        return fee;
    }
}

record FreeShippingAtThreshold(Won threshold, ShippingPolicy basePolicy)
        implements ShippingPolicy {
    FreeShippingAtThreshold {
        Objects.requireNonNull(threshold, "threshold");
        Objects.requireNonNull(basePolicy, "basePolicy");
    }

    @Override
    public Won feeFor(Won subtotal) {
        return subtotal.isAtLeast(threshold) ? Won.ZERO : basePolicy.feeFor(subtotal);
    }
}

record OrderQuote(Won subtotal, Won shippingFee) {
    Won total() {
        return subtotal.plus(shippingFee);
    }
}

record OrderPricing(ShippingPolicy shippingPolicy) {
    OrderPricing {
        Objects.requireNonNull(shippingPolicy, "shippingPolicy");
    }

    OrderQuote quote(OrderLines lines, FulfillmentMethod method) {
        Won subtotal = lines.subtotal();
        Won shippingFee = switch (method) {
            case STORE_PICKUP -> Won.ZERO;
            case DELIVERY -> shippingPolicy.feeFor(subtotal);
        };
        return new OrderQuote(subtotal, shippingFee);
    }
}
```

`new FreeShippingAtThreshold(new Won(50_000), new FlatRateShipping(new Won(3_000)))`을 `OrderPricing`에 전달하면 아래처럼 견적을 계산한다.

| 주문 소계 | 수령 방식 | 배송비 | 최종 금액 |
| --- | --- | --- | --- |
| 25,000원 | 택배 배송 | 3,000원 | 28,000원 |
| 50,000원 | 택배 배송 | 0원 | 50,000원 |
| 25,000원 | 매장 수령 | 0원 | 25,000원 |

## 4. 숨어 있는 도메인 개념 찾기

여러 호출부에서 빈 목록을 검사하고 항목의 단가와 수량을 합산한다면 `OrderLines`라는 개념을 찾을 수 있다. 몇 개의 숫자만 넘겨서 각 값이 소계인지 배송비인지 추적해야 한다면, 계산 결과를 `OrderQuote`로 표현할 수 있다. 추출할 타입의 이름을 업무 대화에서 설명할 수 있는지, 그 타입에 둘 유효성 검사나 연산이 있는지 확인한다. [Martin Fowler의 Replace Primitive with Object](https://refactoring.com/catalog/replacePrimitiveWithObject.html)

| 키워드 | 리뷰 질문 |
| --- | --- |
| 상속과 조합 | 하위 타입이 같은 계약을 지키는가? 바뀌는 정책을 협력 객체로 둘 수 있는가? |
| 값 객체 | 동등성을 판단하는 값, 생성 조건, 계산의 단위가 분명한가? |
| 일급 컬렉션 | 목록의 유효성과 집계 규칙을 한곳에서 적용하는가? |
| Enum과 다형성 | 정해진 선택지와 교체 가능한 동작을 각각 알맞은 타입에 담았는가? |
| 도메인 개념 | 여러 호출부에서 반복하는 판단을 어떤 업무 용어로 부를 수 있는가? |
