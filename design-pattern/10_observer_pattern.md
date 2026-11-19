# Observer Pattern

옵저버 패턴은 한 객체의 상태 변화가 여러 객체에 알려져야 할 때 알림을 구독으로 표현한다. 상품 가격이 바뀌면 가격 표시 화면과 변경 이력이 모두 반응할 수 있다. 가격을 관리하는 객체는 등록된 수신자의 공통 계약으로 변경을 알린다.

## 구조와 선택 기준

- 발행 대상인 `PriceTracker`가 가격과 등록 목록을 관리한다.
- 관찰자는 가격 변경을 받을 때 실행할 콜백을 등록한다. 관찰이 끝나면 등록을 해제한다.
- 가격 변경을 확정한 뒤 새 값을 알려 준다. 예제는 호출한 스레드에서 콜백을 차례로 실행한다.

동기 콜백은 호출 흐름을 따르기 쉽다. 느린 수신자가 호출을 지연시키거나 한 수신자의 예외가 후속 알림을 중단시킬 수 있으므로, 실제 시스템에서는 오류 처리와 관찰자의 수명 주기를 정한다. [발행–구독](23_publisher_subscriber_pattern.md)은 보통 채널과 중개자를 두어 발행자와 구독자의 실행 경계까지 분리한다. Java의 기존 `Observable`과 `Observer`는 Java 9부터 사용 중단으로 표시되어 있다. [Java 17 Observer](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Observer.html)

## Java 17 예제

```java
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntConsumer;

class ObserverExample {
    static final class PriceTracker {
        private final List<IntConsumer> observers = new ArrayList<>();
        private int price;

        PriceTracker(int initialPrice) {
            price = initialPrice;
        }

        void subscribe(IntConsumer observer) {
            observers.add(observer);
        }

        void unsubscribe(IntConsumer observer) {
            observers.remove(observer);
        }

        void changePrice(int nextPrice) {
            if (price == nextPrice) {
                return;
            }
            price = nextPrice;
            for (IntConsumer observer : List.copyOf(observers)) {
                observer.accept(nextPrice);
            }
        }
    }

    public static void main(String[] args) {
        var tracker = new PriceTracker(1_000);
        var display = new ArrayList<Integer>();
        var history = new ArrayList<Integer>();
        IntConsumer updateDisplay = display::add;
        tracker.subscribe(updateDisplay);
        tracker.subscribe(history::add);

        tracker.changePrice(1_200);
        tracker.unsubscribe(updateDisplay);
        tracker.changePrice(1_500);
        tracker.changePrice(1_500);

        if (!display.equals(List.of(1_200)) || !history.equals(List.of(1_200, 1_500))) {
            throw new AssertionError("Notify active observers once per change");
        }
    }
}
```

화면은 구독 중 확인한 1,200원만 받고, 변경 이력은 1,200원과 1,500원을 받는다.

참고 [Design Patterns · Observer](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610) · [Azure Publisher-Subscriber 패턴](https://learn.microsoft.com/azure/architecture/patterns/publisher-subscriber)
