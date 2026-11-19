# Publisher-Subscriber Pattern

주문 확정처럼 하나의 사건에 여러 기능이 반응할 때, 발행자는 사건을 주제에 발행하고 중개자가 관심 있는 구독자에게 전달한다. 발행자는 구독자의 이름과 개수를 알 필요가 없다. 발행자와 구독자는 주제와 메시지 형식을 공통 계약으로 사용한다. [Microsoft의 Publisher-Subscriber 패턴](https://learn.microsoft.com/en-us/azure/architecture/patterns/publisher-subscriber)

## 주제별로 구독자에게 전달하기

예제의 중개자는 같은 프로세스에서 콜백을 동기 호출한다. 주문 확정 주제를 구독한 영수증 처리와 통계 처리에 같은 주문 ID를 전달한다.

```java
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

class PublisherSubscriberExample {
    enum Topic { ORDER_CONFIRMED, ORDER_CANCELED }

    record OrderEvent(long orderId) {}

    static final class EventBus {
        private final Map<Topic, List<Consumer<OrderEvent>>> subscribers =
                new EnumMap<>(Topic.class);

        void subscribe(Topic topic, Consumer<OrderEvent> subscriber) {
            subscribers.computeIfAbsent(topic, ignored -> new ArrayList<>()).add(subscriber);
        }

        void publish(Topic topic, OrderEvent event) {
            var listeners = List.copyOf(subscribers.getOrDefault(topic, List.of()));
            for (var listener : listeners) {
                listener.accept(event);
            }
        }
    }

    public static void main(String[] args) {
        var bus = new EventBus();
        var receiptOrders = new ArrayList<Long>();
        var analyticsOrders = new ArrayList<Long>();
        var canceledOrders = new ArrayList<Long>();
        bus.subscribe(Topic.ORDER_CONFIRMED, event -> receiptOrders.add(event.orderId()));
        bus.subscribe(Topic.ORDER_CONFIRMED, event -> analyticsOrders.add(event.orderId()));
        bus.subscribe(Topic.ORDER_CANCELED, event -> canceledOrders.add(event.orderId()));

        bus.publish(Topic.ORDER_CONFIRMED, new OrderEvent(42));
        if (!receiptOrders.equals(List.of(42L))
                || !analyticsOrders.equals(List.of(42L))
                || !canceledOrders.isEmpty()) {
            throw new AssertionError("Unexpected subscribers received the event");
        }
    }
}
```

두 주문 확정 구독자만 주문 42를 받는다. 예제에서는 한 스레드에서 구독과 발행을 수행하며, 콜백의 예외는 발행 호출로 전파된다. 프로세스를 나누는 실제 브로커에서는 배달 보장, 중복 처리, 순서와 재시도 정책을 제품 및 구성에 맞춰 확인한다.

## Observer와 비교하기

[Observer](10_observer_pattern.md)에서는 관심 대상 객체에 관찰자를 연결한다. 발행·구독에서는 구독 등록과 라우팅을 중개자에 맡긴다. 알림을 동기 또는 비동기로 처리하는지는 실행 모델의 선택이다. [Redis Pub/Sub과 Streams의 전달 특성](../redis/02_redis_pub_sub_and_streams_messaging_patterns.md)
