# Object-Oriented Design and SOLID Principles

[추상화와 메서드 설계](01_abstraction_naming_and_method_design.md)에서는 이름으로 코드의 의도를 드러냈다. 객체 지향 설계에서는 이 의도를 객체의 책임과 협력으로 표현한다. 각 객체가 무엇을 판단하고 누구에게 무엇을 요청하는지 정하면, 변경 요구가 들어왔을 때 수정할 범위를 예측하기 쉬워진다.

## 1. 객체의 책임과 협력 정하기

먼저 구현할 시나리오를 문장으로 써 본다. 예를 들어 주문을 확정할 때는 주문 합계에서 할인액을 빼고, 확정된 주문을 저장한 뒤 호출자에게 돌려준다. 이 흐름에서 할인 규칙과 저장 방식은 서로 다른 요구에 따라 바뀔 수 있다.

| 책임 | 협력에서 하는 일 |
| --- | --- |
| 주문 초안 | 주문 식별자와 합계를 담고, 음수 합계의 생성을 막는다. |
| 주문 확정 | 할인액을 요청하고, 최종 금액으로 주문을 확정해 저장하도록 요청한다. |
| 할인 정책 | 입력 합계에 적용할 할인액을 계산한다. |
| 확정 주문 저장 | 확정된 값을 저장한다. 호출자는 저장할 데이터와 성공 또는 실패를 다룬다. |

호출자가 보는 추상화는 각 책임이 제공하는 연산과 계약이다. 계약에는 허용하는 입력, 보장하는 결과, 상태 변경 여부와 실패 동작을 담는다. 할인 정책의 계산 방식과 저장의 세부 기술은 해당 책임 아래에서 다룬다.

## 2. SOLID를 설계 질문으로 읽기

| 원칙 | 설계 질문 | 주문 확정 예제에 적용 |
| --- | --- | --- |
| **SRP** · Single Responsibility Principle | 같은 요구에 따라 바뀌는 코드가 한곳에 모여 있는가? | 주문 확정의 순서, 할인율, 저장 기술은 변경 이유가 다르므로 책임을 나눈다. |
| **OCP** · Open-Closed Principle | 예상한 변경을 새 구현으로 추가할 수 있는가? | 동일한 할인 계약을 지키는 새 정책을 주입해 주문 확정 흐름을 재사용한다. |
| **LSP** · Liskov Substitution Principle | 구현을 교체해도 호출자가 기대하는 계약이 유지되는가? | 모든 할인 정책은 유효한 주문 합계를 받고, 0원 이상이며 합계를 넘지 않는 할인액을 반환한다. |
| **ISP** · Interface Segregation Principle | 호출자가 자신의 작업에 필요한 연산만 의존하는가? | 주문 확정은 저장 역할을 사용한다. 주문 검색이나 통계 조회가 필요하다면 이를 사용하는 쪽에 맞춰 계약을 둔다. |
| **DIP** · Dependency Inversion Principle | 업무 흐름과 구현 세부 사항이 어느 추상화에 의존하는가? | 업무 코드가 필요로 하는 저장 계약을 먼저 정한다. 주문 확정과 구체 저장 구현이 그 계약을 향하도록 구성한다. |

SRP를 판단할 때는 담당하는 기능 수와 함께 코드가 **누구의 요구로 함께 바뀌는지**를 본다. OCP를 적용할 변경 축도 구체적으로 정한다. 이 예제에서 해당 축은 할인액의 계산 방식이다. 할인 규칙이 주문 이력 같은 새 입력을 요구하면 계약 자체를 검토한다. [Robert C. Martin의 단일 책임 원칙](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html) · [Design Principles and Design Patterns](https://wnmurphy.com/assets/pdf/Robert_C._Martin_-_2000_-_Principles_and_Patterns.pdf)

## 3. 같은 주문 확정 흐름에서 할인 정책 교체하기

아래 예제는 금액을 원 단위 정수로 다룬다. 10% 할인에서 원 미만 금액은 버린다. 주문 확정은 할인액을 구해 합계에서 차감한 뒤, 계산한 결과를 한 번 저장한다.

```java
record OrderDraft(String orderId, int subtotalWon) {
    OrderDraft {
        if (subtotalWon < 0) {
            throw new IllegalArgumentException("subtotalWon must be non-negative");
        }
    }
}

record ConfirmedOrder(String orderId, int totalWon) {}

interface DiscountPolicy {
    // 입력은 0 이상이고, 할인액은 0 이상이며 입력값 이하다.
    int discountFor(int subtotalWon);
}

final class NoDiscount implements DiscountPolicy {
    @Override
    public int discountFor(int subtotalWon) {
        return 0;
    }
}

final class TenPercentDiscount implements DiscountPolicy {
    @Override
    public int discountFor(int subtotalWon) {
        return subtotalWon / 10;
    }
}

interface OrderWriter {
    // 확정 주문을 저장한다. 실패하면 호출자에게 예외로 알린다.
    void save(ConfirmedOrder order);
}

final class Checkout {
    private final DiscountPolicy discountPolicy;
    private final OrderWriter orderWriter;

    Checkout(DiscountPolicy discountPolicy, OrderWriter orderWriter) {
        this.discountPolicy = discountPolicy;
        this.orderWriter = orderWriter;
    }

    ConfirmedOrder confirm(OrderDraft order) {
        int discountWon = discountPolicy.discountFor(order.subtotalWon());
        var confirmed = new ConfirmedOrder(order.orderId(), order.subtotalWon() - discountWon);
        orderWriter.save(confirmed);
        return confirmed;
    }
}
```

합계가 12,345원이면 `NoDiscount`는 12,345원, `TenPercentDiscount`는 11,111원으로 확정한다. 두 정책은 결과가 달라도 할인액의 범위라는 공통 계약을 지킨다. 정책 하나가 10,000원 미만의 정상 입력에 예외를 던지도록 바뀌면 호출자가 받아들일 수 있던 입력의 범위가 좁아진다. 구현의 교체 가능성은 메서드 모양과 함께 입력의 전제, 결과 보장, 상태 규칙을 비교해 판단한다. [Liskov와 Wing의 행동적 하위 타입](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf)

`Checkout`의 생성자에는 사용할 구현을 외부에서 넘긴다. 생성자 주입은 구현을 연결하는 방법이다. DIP는 `Checkout`과 구체 저장 구현이 모두 업무 쪽의 `OrderWriter` 계약에 의존하는 구조에 관한 원칙이다. 실행 시에는 `Checkout`의 저장 요청을 선택한 구현이 처리한다. [Robert C. Martin의 의존성 역전 원칙](https://www.cs.utexas.edu/~downing/papers/DIP-1996.pdf)

## 4. 핵심 키워드로 코드 검토하기

- **책임과 협력** · 업무 시나리오를 읽을 때 누가 어떤 결정을 하고 누구에게 다음 일을 요청하는가?
- **변경 이유와 확장** · 할인 규칙만 바뀌었을 때 어떤 클래스와 테스트를 수정해야 하는가?
- **계약과 대체 가능성** · 구현마다 0원과 일반 주문을 처리할 수 있으며, 반환 범위와 실패 방식이 계약과 맞는가?
- **인터페이스와 의존 방향** · 호출자가 필요한 연산이 무엇이고, 구체 구현을 선택하는 결정은 어디에 있는가?
