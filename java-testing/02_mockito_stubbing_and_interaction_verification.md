# Mockito Stubbing and Interaction Verification

Mockito로 협력 객체의 응답을 제어하고, 테스트 대상이 어떤 요청을 보냈는지 확인할 수 있다. 재고 예약 서비스를 예로 들어 재고 조회 응답은 스텁으로 준비하고, 재고를 실제로 확보해야 하는 경우에만 예약 요청이 전달됐는지 검증한다. 실습 기준은 **Java 17, JUnit 5.12.2, Mockito 5.17.0**이다.

## 1. Mockito 시작하기

스텁은 조회 결과나 실패를 미리 지정한다. 호출 검증은 테스트를 실행한 뒤 어떤 요청이 있었는지 확인한다. 하나의 Mockito 모의 객체에서 두 기능을 함께 사용할 수 있다. [Mockito API](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/Mockito.java) · [Test Doubles and Mockito](../practical-testing/05_test_doubles_and_mockito.md)

[JUnit 5 문서](01_junit_5_fundamentals_and_extensions.md)의 Gradle 테스트 설정에 다음 의존성을 추가한다. 이 모듈은 Jupiter 확장과 Mockito 코어를 제공한다. 아래 Java 예제는 같은 테스트 패키지에 둔다. [MockitoExtension](https://github.com/mockito/mockito/blob/v5.17.0/mockito-extensions/mockito-junit-jupiter/src/main/java/org/mockito/junit/jupiter/MockitoExtension.java)

```groovy
dependencies {
    testImplementation 'org.mockito:mockito-junit-jupiter:5.17.0'
}
```

## 2. 모의 객체를 만들고 테스트 대상에 전달

`mock(InventoryGateway.class)`는 인터페이스를 구현하는 모의 객체를 만든다. 테스트에서 생성자를 호출해 어떤 대역이 들어가는지 드러낼 수 있다. 반복되는 선언은 `@Mock`과 `@ExtendWith(MockitoExtension.class)`로 줄일 수 있다. [Mockito API](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/Mockito.java) · [MockitoExtension](https://github.com/mockito/mockito/blob/v5.17.0/mockito-extensions/mockito-junit-jupiter/src/main/java/org/mockito/junit/jupiter/MockitoExtension.java)

```java
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

interface InventoryGateway {
    int available(String sku);

    void hold(String sku, int quantity);
}

final class StockReservation {
    private final InventoryGateway inventory;

    StockReservation(InventoryGateway inventory) {
        this.inventory = inventory;
    }

    boolean reserve(String sku, int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("Quantity must be positive");
        }
        if (inventory.available(sku) < quantity) {
            return false;
        }
        inventory.hold(sku, quantity);
        return true;
    }
}

class ManualMockTest {
    @Test
    void holdsTheRequestedStock() {
        InventoryGateway inventory = mock(InventoryGateway.class);
        var reservation = new StockReservation(inventory);
        when(inventory.available("MUG")).thenReturn(5);

        boolean reserved = reservation.reserve("MUG", 2);

        assertTrue(reserved);
        verify(inventory).hold("MUG", 2);
    }
}
```

## 3. 스터빙 · 정상 응답과 실패 응답

| 준비 방식 | 사용할 때 |
| --- | --- |
| `when(call).thenReturn(value)` | 반환값이 있는 호출의 응답을 지정한다. |
| `when(call).thenThrow(exception)` | 값을 반환하는 호출에서 예외를 재현한다. |
| `doThrow(exception).when(mock).method(...)` | 반환값이 없는 `void` 메서드의 실패를 재현한다. |
| `when(call).thenReturn(first, second)` | 동일한 호출을 반복할 때 응답이 달라지는 상황을 만든다. 지정한 응답을 다 사용하면 마지막 응답을 계속 반환한다. |

스텁이 없는 메서드의 기본 응답은 반환 타입에 따라 다르다. 예를 들어 `int`의 기본 응답은 `0`이다. 부족한 재고나 조회 실패처럼 시나리오에 중요한 응답은 명시한다. `MockitoExtension`의 기본 엄격성인 `STRICT_STUBS`는 사용하지 않은 스텁이나 일부 인자 불일치를 발견하는 데 도움이 된다. 공통 설정에는 여러 테스트가 실제로 사용하는 스텁만 둔다. [Mockito API](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/Mockito.java) · [Strictness](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/quality/Strictness.java)

```java
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ReservationStubbingTest {
    @Mock
    InventoryGateway inventory;

    private StockReservation reservation;

    @BeforeEach
    void setUp() {
        reservation = new StockReservation(inventory);
    }

    @Test
    void leavesStockUnchangedWhenAvailabilityIsTooLow() {
        when(inventory.available("MUG")).thenReturn(1);

        assertFalse(reservation.reserve("MUG", 2));

        verify(inventory, never()).hold(any(), anyInt());
    }

    @Test
    void propagatesHoldFailure() {
        var failure = new IllegalStateException("Inventory write failed");
        when(inventory.available("MUG")).thenReturn(5);
        doThrow(failure).when(inventory).hold("MUG", 2);

        var thrown = assertThrows(
                IllegalStateException.class, () -> reservation.reserve("MUG", 2)
        );

        assertSame(failure, thrown);
    }
}
```

## 4. 연습 · 재고가 늘어난 뒤에만 예약

동일한 상품을 두 번 요청한다. 두 개를 예약하려는데 첫 조회에서 재고가 한 개이고 다음 조회에서 다섯 개라면, 첫 요청은 거부되고 두 번째 요청만 재고를 확보해야 한다. 연속한 반환값으로 이를 재현하고 실제 확보 요청의 상품과 수량을 확인한다.

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ReservationPracticeTest {
    @Mock
    InventoryGateway inventory;

    @Test
    void holdsStockOnlyAfterInventoryIsReplenished() {
        var reservation = new StockReservation(inventory);
        when(inventory.available("MUG")).thenReturn(1, 5);

        assertFalse(reservation.reserve("MUG", 2));
        assertTrue(reservation.reserve("MUG", 2));

        ArgumentCaptor<Integer> quantity = ArgumentCaptor.forClass(Integer.class);
        verify(inventory).hold(eq("MUG"), quantity.capture());
        assertEquals(2, quantity.getValue());
    }
}
```

## 5. 호출 횟수와 인자를 검증

`verify(mock)`는 지정한 인자로 한 번 호출됐는지 확인한다. `times(n)`은 정확한 횟수를, `never()`는 지정한 호출이 없었는지를 확인한다. `verifyNoInteractions(mock)`는 그 객체에 대한 모든 호출이 없었는지 검사한다. 재고를 조회한 뒤 확보만 생략해야 하는 시나리오에는 `never()`로 확보 호출을 검증한다. [Mockito API](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/Mockito.java)

한 호출에서 매처나 캡처를 쓰면 같은 호출의 나머지 인자도 `eq(...)` 같은 매처로 표현한다. 값이 이미 정해져 있으면 인자를 그대로 검증해도 된다. `ArgumentCaptor`는 보내진 인자의 여러 필드를 따로 단언할 때 적합하다. `InOrder`는 호출 순서가 계약에 포함될 때 사용한다. [ArgumentMatchers](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/ArgumentMatchers.java) · [ArgumentCaptor](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/ArgumentCaptor.java)

## 6. Given–When–Then과 BDDMockito

Given에서는 `given(...).willReturn(...)`으로 응답을 준비한다. When에서는 테스트 대상의 동작을 실행한다. Then에서는 결과를 단언하고 `then(mock).should()`로 필요한 호출을 검증한다. BDD API는 같은 스터빙과 검증을 테스트 단계에 맞춘 이름으로 표현한다. [BDDMockito API](https://github.com/mockito/mockito/blob/v5.17.0/mockito-core/src/main/java/org/mockito/BDDMockito.java)

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;

@ExtendWith(MockitoExtension.class)
class ReservationBddTest {
    @Mock
    InventoryGateway inventory;

    @Test
    void reservesTheRemainingStock() {
        var reservation = new StockReservation(inventory);
        given(inventory.available("TEA")).willReturn(3);

        boolean reserved = reservation.reserve("TEA", 3);

        assertTrue(reserved);
        then(inventory).should().hold("TEA", 3);
    }
}
```
