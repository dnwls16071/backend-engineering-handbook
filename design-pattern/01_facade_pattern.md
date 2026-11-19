# Facade Pattern

파사드는 여러 구성 요소가 협력하는 작업을 하나의 진입점으로 제공하는 구조 패턴이다. 호출자는 필요한 업무 동작을 요청하고, 파사드는 내부 구성 요소를 호출하는 순서와 결과 조합을 맡는다. [GoF의 Facade](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 어떤 문제를 푸는가

매장 수령 요청을 만들려면 재고를 예약하고 수령표를 발급해야 한다. 앱과 매장 단말이 두 서비스를 각각 호출하면 호출 순서와 두 결과를 조합하는 규칙이 여러 곳으로 퍼진다. `PickupFacade`에 수령 준비 작업을 두면 각 호출자는 주문 번호와 상품 코드만 전달할 수 있다.

## Java 17 예제

```java
public class FacadeExample {
    record PickupRequest(String reservationId, String ticketId) {}

    static final class StockService {
        String reserve(String productCode) {
            return "stock-" + productCode;
        }
    }

    static final class TicketService {
        String issue(String orderId, String reservationId) {
            return orderId + "/" + reservationId;
        }
    }

    record PickupFacade(StockService stock, TicketService tickets) {
        PickupRequest prepare(String orderId, String productCode) {
            String reservationId = stock.reserve(productCode);
            String ticketId = tickets.issue(orderId, reservationId);
            return new PickupRequest(reservationId, ticketId);
        }
    }

    public static void main(String[] args) {
        var facade = new PickupFacade(new StockService(), new TicketService());
        var request = facade.prepare("order-21", "P-7");
        var expected = new PickupRequest("stock-P-7", "order-21/stock-P-7");
        if (!request.equals(expected)) {
            throw new AssertionError(request);
        }
        System.out.println(request.ticketId());
    }
}
```

실행 결과는 `order-21/stock-P-7`이다. 수령표는 재고 예약 ID를 사용하므로 두 호출의 순서가 명확하다.

## 적용할 때 볼 점

- 자주 쓰는 작업 몇 개를 중심으로 진입점을 두면 호출부의 의존 범위가 줄어든다. 업무 흐름이 서로 다르면 파사드도 별도로 둘 수 있다.
- 외부 구성 요소를 차례로 호출하는 것만으로 전체 작업의 원자성이 생기지는 않는다. 재고 예약이 성공한 뒤 수령표 발급이 실패할 수 있다면 재시도나 예약 취소 정책을 결정한다.
- 파사드는 여러 구성 요소를 쓰기 쉽게 묶는다. 어댑터는 호출자가 기대하는 인터페이스에 기존 구현을 맞춘다. [Adapter Pattern](06_adapter_pattern.md)
