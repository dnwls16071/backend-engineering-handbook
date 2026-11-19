# Factory Method Pattern

팩토리 메서드 패턴은 공통 작업을 수행하는 상위 타입에서 객체 생성 단계를 메서드로 정의하고, 하위 타입이 그 생성 메서드를 재정의하게 한다. 인도 라벨을 준비하는 흐름은 같아도 택배와 매장 수령에는 서로 다른 라벨이 필요할 수 있다.

## 구조와 선택 기준

- 생성자인 `HandoffWorkflow`는 라벨을 만들고 출력 문구를 준비하는 흐름을 제공한다.
- 팩토리 메서드 `createLabel`이 반환하는 공통 제품 타입은 `Label`이다.
- 구체 생성자는 택배 또는 매장 수령 라벨을 선택한다. 상위 흐름은 제품의 공통 계약을 사용한다.

이미 여러 작업 유형이 공통 흐름을 공유하고 객체 생성 단계가 유형마다 달라질 때 적합하다. 한 메서드가 인자를 분기해 객체를 고르는 단순 팩토리와 비교할 때, 여기서 생성 선택의 위치는 하위 타입의 재정의다. 관련 제품 여러 개를 호환되는 세트로 구성해야 한다면 [추상 팩토리](12_abstract_factory_pattern.md)를 검토한다.

## Java 17 예제

```java
class FactoryMethodExample {
    interface Label {
        String format(String orderId);
    }

    static final class CourierLabel implements Label {
        @Override
        public String format(String orderId) {
            return "courier/" + orderId;
        }
    }

    static final class PickupLabel implements Label {
        @Override
        public String format(String orderId) {
            return "pickup/" + orderId;
        }
    }

    abstract static class HandoffWorkflow {
        final String prepare(String orderId) {
            return "Label ready: " + createLabel().format(orderId);
        }

        protected abstract Label createLabel();
    }

    static final class CourierWorkflow extends HandoffWorkflow {
        @Override
        protected Label createLabel() {
            return new CourierLabel();
        }
    }

    static final class PickupWorkflow extends HandoffWorkflow {
        @Override
        protected Label createLabel() {
            return new PickupLabel();
        }
    }

    public static void main(String[] args) {
        if (!new CourierWorkflow().prepare("A12").equals("Label ready: courier/A12")
                || !new PickupWorkflow().prepare("A12").equals("Label ready: pickup/A12")) {
            throw new AssertionError("The creator should choose the matching label");
        }
    }
}
```

호출자는 동일한 `prepare` 흐름을 사용하고, 선택한 하위 타입에 따라 라벨만 달라진다. 생성 외의 작업 순서까지 여러 단계로 고정하는 구조는 [템플릿 메서드](03_template_method_pattern.md)에서 다룬다.

참고 [Design Patterns · Factory Method](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)
