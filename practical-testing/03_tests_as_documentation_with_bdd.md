# Tests as Documentation with BDD

테스트는 특정 조건에서 시스템이 어떻게 동작하는지를 실행 가능한 예로 남긴다. 이름과 검증 결과를 함께 읽으면 어떤 업무 규칙이 깨졌는지 좁힐 수 있다. 검증할 행동을 먼저 문장으로 쓰고, 그 행동에 필요한 준비와 관찰 가능한 결과를 코드로 옮긴다.

## 1. 행동이 드러나는 표시 이름

`reserveTest`나 `성공 테스트`는 실패했을 때 검증하던 조건을 알기 어렵다. “재고가 3개인 상품을 2개 예약하면 남은 재고는 1개다”처럼 판정을 바꾸는 조건과 행동, 결과를 담으면 테스트 보고서에서도 규칙을 읽을 수 있다. JUnit Jupiter의 `@DisplayName`은 클래스와 메서드의 표시 이름을 지정하므로 Java 식별자와 별개로 문장을 쓸 수 있다. [JUnit 5 표시 이름](https://docs.junit.org/5.13.4/user-guide/#writing-tests-display-names)

표시 이름은 호출 메서드의 이름이나 내부 분기보다 사용자가 기대하는 의미를 표현한다. 재고 예약의 성공과 재고 부족에 따른 거절처럼 업무 결과가 달라지는 경우에는 시나리오를 각각 둔다.

## 2. Given, When, Then으로 시나리오 쓰기

| 단계 | 읽는 사람이 확인할 내용 | 재고 예약 예시 |
| --- | --- | --- |
| Given | 이번 행동에 영향을 주는 사전 상태 | 예약 가능한 재고가 3개 있다. |
| When | 결과를 검증할 행동 | 상품 2개를 예약한다. |
| Then | 외부에서 관찰할 수 있는 결과 | 남은 재고는 1개다. |

Given, When, Then은 시나리오의 맥락, 행동, 결과를 나누는 표현이다. JUnit 테스트에서도 준비, 호출, 단언을 읽는 순서에 맞게 배치할 수 있다. 팀 간 협업에서는 이 문장으로 기대 동작을 먼저 합의하고, 합의한 내용을 코드의 검증 결과와 연결한다. [Cucumber의 Given, When, Then](https://cucumber.io/docs/gherkin/reference/) · [테스트 시나리오와 API 단언](../test-driven-development/02_test_scenarios_and_api_assertions.md)

## 3. JUnit 5로 예약 규칙 기록하기

아래 예제에서 예약에 성공하면 남은 재고를 나타내는 새 값이 반환된다. 재고를 초과한 요청은 예외로 거절한다. 성공 테스트의 단언은 상태 변화의 결과를, 거절 테스트의 단언은 호출자가 받을 실패 유형을 확인한다. 두 테스트는 사전 상태를 각자 준비한다. [JUnit 5 단언과 예외 검증](https://docs.junit.org/5.13.4/user-guide/#writing-tests-assertions)

```java
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class ReservationDocumentationTest {
    @Test
    @DisplayName("재고가 3개인 상품을 2개 예약하면 남은 재고는 1개다")
    void reservesAvailableStock() {
        // Given
        var stock = new BddStock(3);

        // When
        var remaining = stock.reserve(2);

        // Then
        assertEquals(1, remaining.quantity());
    }

    @Test
    @DisplayName("요청 수량이 남은 재고를 초과하면 예약을 거절한다")
    void rejectsReservationExceedingAvailableStock() {
        // Given
        var stock = new BddStock(1);

        // When & Then
        assertThrows(IllegalStateException.class, () -> stock.reserve(2));
    }
}

record BddStock(int quantity) {
    BddStock reserve(int requested) {
        if (requested <= 0) {
            throw new IllegalArgumentException("Requested quantity must be positive");
        }
        if (requested > quantity) {
            throw new IllegalStateException("Insufficient stock");
        }
        return new BddStock(quantity - requested);
    }
}
```

`assertThrows`에는 거절을 일으키는 호출을 넘긴다. 이렇게 하면 객체 준비 단계와 예약 요청에서 발생한 예외를 구분할 수 있다. 테스트를 검토할 때는 표시 이름의 조건과 Given의 데이터가 일치하는지, Then의 단언이 그 조건의 결과를 직접 관찰하는지 확인한다. [JUnit 5의 assertThrows](https://docs.junit.org/5.13.4/user-guide/#writing-tests-exception-handling)
