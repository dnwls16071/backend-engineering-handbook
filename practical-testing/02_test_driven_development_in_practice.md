# Test-Driven Development in Practice

테스트 주도 개발은 구현할 동작을 실행 가능한 예시로 먼저 표현하고, 예시 하나씩 만족하면서 설계를 다듬는 방식이다. 좌석 예약을 예로 들면 남은 좌석 수를 줄이기 전에 요청 수량, 허용 조건, 실패했을 때 남을 상태를 호출자 관점에서 정한다. [Martin Fowler의 Test Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

## 1. 관찰할 동작을 작게 나누기

| 사례 | 호출자가 확인하는 결과 |
| --- | --- |
| 남은 좌석 3개에서 1개 예약 | 남은 좌석은 2개다. |
| 남은 좌석 3개에서 3개 예약 | 남은 좌석은 0개다. |
| 남은 좌석 3개에서 4개 요청 | 좌석 부족 오류가 발생하고, 남은 좌석은 3개다. |
| 예약 수량으로 0개 요청 | 잘못된 입력이라는 오류가 발생한다. |

각 사례가 추가될 때마다 앞서 확인한 사례도 함께 실행한다. 호출자가 사용할 `reserve`와 `remainingSeats`를 먼저 정하면, 구현을 작성하기 전에 호출 방식과 반환 계약을 검토할 수 있다. [TDD의 시나리오 목록과 피드백 루프](../test-driven-development/01_tdd_fundamentals_and_feedback_loops.md)

## 2. Red → Green → Refactor로 반복하기

1. Red에서는 사례 하나를 작성해 아직 해당 동작이 구현되지 않았음을 확인한다. 예를 들어 예약 전후에 잔여 수량을 3으로 반환하는 구현에서 1개를 예약하면, 첫 테스트는 기대값 2와 실제값 3이 달라 실패한다.
2. Green에서는 예약 성공 시 수량을 차감하는 구현을 추가하고 테스트를 실행한다. 다음 사례로 정확히 3개를 예약하는 경계를 추가하고, 이후 좌석 부족과 잘못된 수량을 처리한다.
3. Refactor에서는 테스트를 계속 실행하며 검증 흐름의 이름과 위치를 다듬는다. 예를 들어 수량 조건을 `validateRequest`에 모아 두면 `reserve`에서 검증 후 차감한다는 흐름을 읽을 수 있다.

실패한 이유가 예상과 같은지 출력에서 확인하면 구현으로 넘어갈 기준이 분명해진다. 새 테스트가 바로 통과했다면 기존 구현에서 해당 동작이 이미 성립하는지, 단언이 의도한 결과를 확인하는지 살펴본다.

## 3. 한 주기를 마친 예제

아래 Java 예제는 앞의 네 사례가 모두 실행되는 상태다. 좌석 부족 테스트에는 실패 후 상태까지 포함해 잘못된 차감이 발생하면 드러나게 한다. `assertThrows`의 실행 람다에는 검사하려는 호출을 넣는다. [JUnit 5의 예외 단언](https://docs.junit.org/5.13.4/user-guide/#writing-tests-assertions)

```java
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

final class TddSeatPool {
    private int remainingSeats;

    TddSeatPool(int capacity) {
        if (capacity < 0) {
            throw new IllegalArgumentException("capacity must be non-negative");
        }
        remainingSeats = capacity;
    }

    void reserve(int quantity) {
        validateRequest(quantity);
        remainingSeats -= quantity;
    }

    int remainingSeats() {
        return remainingSeats;
    }

    private void validateRequest(int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive");
        }
        if (quantity > remainingSeats) {
            throw new IllegalStateException("not enough seats");
        }
    }
}

class TddSeatPoolTest {
    @Test
    void reducesTheRemainingSeatsAfterReservation() {
        var seats = new TddSeatPool(3);

        seats.reserve(1);

        assertEquals(2, seats.remainingSeats());
    }

    @Test
    void acceptsAllRemainingSeats() {
        var seats = new TddSeatPool(3);

        seats.reserve(3);

        assertEquals(0, seats.remainingSeats());
    }

    @Test
    void rejectsAnExcessRequestAndKeepsTheRemainingSeats() {
        var seats = new TddSeatPool(3);

        assertThrows(IllegalStateException.class, () -> seats.reserve(4));

        assertEquals(3, seats.remainingSeats());
    }

    @Test
    void rejectsAZeroQuantity() {
        var seats = new TddSeatPool(3);

        assertThrows(IllegalArgumentException.class, () -> seats.reserve(0));
    }
}
```

| 키워드 | 확인할 질문 |
| --- | --- |
| Red | 다음에 추가할 사례가 예상한 이유로 실패하는가? |
| Green | 이번 사례와 기존 사례가 함께 통과하는가? |
| Refactor | 공개 동작이 유지되면서 구현의 의도가 더 분명해졌는가? |
