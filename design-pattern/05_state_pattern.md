# State Pattern

상태는 객체의 현재 단계에 따라 동작을 위임하는 행동 패턴이다. 각 상태에 허용된 동작과 전이를 표현하면 여러 메서드에 흩어진 단계별 분기를 한곳에서 찾을 수 있다. [GoF의 State](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 어떤 문제를 푸는가

주문 처리에서 같은 진행 요청을 받아도 결제를 기다리는 주문과 출고 준비가 끝난 주문은 다음 단계가 다르다. 주문이 내부에 현재 상태를 보관하고, 상태가 진행 요청의 결과로 다음 상태를 돌려주게 한다. 이 예제에서 진행 요청은 현재 단계의 작업이 완료된 뒤 들어온다.

## Java 17 예제

```java
public class StateExample {
    enum OrderState {
        AWAITING_PAYMENT {
            @Override
            OrderState advance() {
                return READY_TO_SHIP;
            }
        },
        READY_TO_SHIP {
            @Override
            OrderState advance() {
                return SHIPPED;
            }
        },
        SHIPPED {
            @Override
            OrderState advance() {
                throw new IllegalStateException("The order has already shipped");
            }
        };

        abstract OrderState advance();
    }

    static final class Order {
        private OrderState state = OrderState.AWAITING_PAYMENT;

        void advance() {
            state = state.advance();
        }

        OrderState state() {
            return state;
        }
    }

    public static void main(String[] args) {
        var order = new Order();
        order.advance();
        if (order.state() != OrderState.READY_TO_SHIP) {
            throw new AssertionError(order.state());
        }
        order.advance();
        if (order.state() != OrderState.SHIPPED) {
            throw new AssertionError(order.state());
        }
        try {
            order.advance();
            throw new AssertionError("Expected the shipped state to reject advancement");
        } catch (IllegalStateException expected) {
            System.out.println(order.state());
        }
    }
}
```

실행 결과는 `SHIPPED`다. 주문은 결제 대기에서 출고 준비를 거쳐 출고 완료로 이동하고, 완료 단계에서 다시 진행하면 예외가 발생한다.

## 적용할 때 볼 점

- 상태별 동작이 여러 곳에서 반복되는지 확인한다. 단일 전이 표로 충분한 규모라면 표나 열거형 분기만으로도 읽기 쉬울 수 있다.
- 상태 간 관계가 타입에 분산될 수 있다. 가능한 전이와 거부할 전이를 테스트에 남기면 새 상태를 추가할 때 누락을 찾기 쉽다.
- 전략은 교체 가능한 알고리즘을 제공하는 데 쓰고, 상태는 객체의 수명 주기와 단계별 동작을 표현하는 데 쓴다. [Strategy Pattern](02_strategy_pattern.md)
