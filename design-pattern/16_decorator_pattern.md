# Decorator Pattern

객체에 부가 기능을 조합해 붙여야 할 때, 같은 인터페이스를 구현한 래퍼에 기존 객체를 담을 수 있다. 데코레이터는 기존 객체에 처리를 위임하면서 호출 전후에 자신의 동작을 더한다. 여러 데코레이터를 겹쳐 사용하면 필요한 기능 조합을 실행 시점에 구성할 수 있다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 배송 라벨의 표시 추가하기

```java
public class DecoratorExample {
    interface Label {
        String render();
    }

    record ShippingLabel(String orderId) implements Label {
        public String render() {
            return orderId;
        }
    }

    record FragileLabel(Label wrapped) implements Label {
        public String render() {
            return "[FRAGILE] " + wrapped.render();
        }
    }

    record PriorityLabel(Label wrapped) implements Label {
        public String render() {
            return "[PRIORITY] " + wrapped.render();
        }
    }

    public static void main(String[] args) {
        Label base = new ShippingLabel("ORDER-17");
        Label combined = new PriorityLabel(new FragileLabel(base));
        if (!combined.render().equals("[PRIORITY] [FRAGILE] ORDER-17")
                || !base.render().equals("ORDER-17")) {
            throw new AssertionError("Unexpected label");
        }
    }
}
```

라벨의 기본 출력은 `ORDER-17`이고, 두 표시를 조합하면 `[PRIORITY] [FRAGILE] ORDER-17`이 된다. 호출자는 기본 라벨과 조합된 라벨을 동일한 `Label` 인터페이스로 사용한다.

## 적용할 때 확인할 점

부가 기능이 서로 독립적이고 기능의 조합이 여러 가지라면 데코레이터를 고려한다. 처리 순서가 출력이나 예외 처리에 영향을 주므로 실제 조합을 테스트한다. 래퍼가 많아지면 어느 객체가 어떤 작업을 수행하는지 확인하는 비용이 늘어난다. [Proxy](09_proxy_pattern.md)도 래퍼 구조를 사용할 수 있다. 접근 제어, 지연 초기화, 원격 접근처럼 대상을 대신하는 목적은 Proxy에 해당한다.
