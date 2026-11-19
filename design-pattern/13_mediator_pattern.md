# Mediator Pattern

같은 화면의 구성 요소가 서로의 메서드를 직접 호출하면 규칙이 여러 곳에 분산된다. 중재자 패턴은 구성 요소 사이의 협력 규칙을 중재자에 둔다. 구성 요소는 자신의 상태 변화나 입력 이벤트를 알리고, 중재자가 다른 요소에 반영할 동작을 결정한다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 주문 화면의 협력 조정하기

- `DeliverySelector`는 수령 방식을 저장하고 변경을 알린다.
- `AddressField`는 주소 입력을 관리하고 편집을 알린다.
- `CheckoutForm`은 배송 주소 입력을 활성화할지, 제출 버튼을 사용할 수 있는지 결정한다.

```java
public class MediatorExample {
    enum DeliveryMode { PICKUP, DELIVERY }

    static final class DeliverySelector {
        private final CheckoutForm form;
        private DeliveryMode mode = DeliveryMode.PICKUP;

        DeliverySelector(CheckoutForm form) {
            this.form = form;
        }

        void select(DeliveryMode newMode) {
            mode = newMode;
            form.refresh();
        }
    }

    static final class AddressField {
        private final CheckoutForm form;
        private String text = "";
        private boolean enabled;

        AddressField(CheckoutForm form) {
            this.form = form;
        }

        void edit(String newText) {
            if (!enabled) {
                throw new IllegalStateException("Address field is disabled");
            }
            text = newText;
            form.refresh();
        }
    }

    static final class CheckoutForm {
        private final DeliverySelector delivery = new DeliverySelector(this);
        private final AddressField address = new AddressField(this);
        private boolean canSubmit;

        CheckoutForm() {
            refresh();
        }

        void refresh() {
            boolean requiresAddress = delivery.mode == DeliveryMode.DELIVERY;
            address.enabled = requiresAddress;
            canSubmit = !requiresAddress || !address.text.isBlank();
        }
    }

    public static void main(String[] args) {
        var form = new CheckoutForm();
        if (form.address.enabled || !form.canSubmit) {
            throw new AssertionError("Pickup should be ready without an address");
        }
        form.delivery.select(DeliveryMode.DELIVERY);
        if (!form.address.enabled || form.canSubmit) {
            throw new AssertionError("Delivery should require an address");
        }
        form.address.edit("12 Market Street");
        if (!form.canSubmit) {
            throw new AssertionError("Delivery should now be ready");
        }
    }
}
```

픽업은 주소 없이 제출할 수 있다. 배송을 선택하면 주소가 입력될 때까지 제출이 제한되고, 주소를 입력하면 제출할 수 있다.

## 적용할 때 확인할 점

여러 구성 요소가 함께 바뀌는 화면이나 워크플로에 적합하다. 중재자가 화면 전체의 처리와 업무 규칙까지 맡기 시작하면 관련 흐름을 더 작은 조정 단위로 나눈다. 파사드는 호출자에게 서브시스템 진입점을 제공하고, 중재자는 참여 객체 사이에서 일어나는 협력을 조정한다. [Facade](01_facade_pattern.md)
