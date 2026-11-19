# Abstraction, Naming, and Method Design

프로그램은 컴퓨터가 실행할 동작을 표현하는 동시에, 사람이 문제와 해결 과정을 이해할 수 있게 한다. 읽기 좋은 코드는 중요한 규칙을 이름과 구조로 드러낸다. 코드가 읽히는 순서대로 동작을 설명할 수 있으면 변경할 위치를 찾고, 영향을 받는 규칙을 검토하기 쉬워진다.

## 1. 추상과 구체를 오가며 읽기

추상화는 현재 질문에 필요한 특징을 드러내고 세부 사항은 더 적합한 위치에 둔다. 주문 처리에서 `reserveStock(order)`는 지금 수행할 일을 표현한다. 재고를 어떤 테이블에서 읽고 어떻게 차감하는지는 그 메서드의 구현을 볼 때 필요한 정보다.

추상화 수준은 읽는 맥락에 따라 달라진다. 주문 확정 흐름에서 `reserveStock`은 한 단계지만, 재고 차감 규칙을 검토할 때는 차감 가능 수량과 실패 처리까지 구체적으로 봐야 한다. 읽는 사람이 어떤 질문을 하는지에 맞춰 세부 사항을 배치한다.

## 2. 이름으로 대상과 의도 드러내기

| 모호한 이름 | 의미를 드러낸 이름 | 읽을 때 드러나는 정보 |
| --- | --- | --- |
| `data` | `pendingOrders` | 처리 대기 중인 주문 목록 |
| `amount` | `orderTotalWon` | 배송비 판단에 쓰는 주문 합계와 원 단위 |
| `check` | `isPaymentComplete` | 결제 완료 여부를 반환하는 조회 |
| `process` | `reserveStock` | 재고를 예약하는 동작 |

같은 개념에는 같은 용어를 쓰고, 의미가 다른 값은 이름에서 구분한다. 예를 들어 주문 합계와 실제 결제액은 할인이나 배송비 때문에 달라질 수 있다. 메서드는 동작을 표현하는 동사나 동사구로 쓰고, 조회와 상태 변경은 호출부에서 구분할 수 있는 이름을 붙인다. [Java 언어 명세의 이름 짓기 관례](https://docs.oracle.com/javase/specs/jls/se21/html/jls-6.html#jls-6.1)

## 3. 메서드 선언부에서 호출 계약 읽기

`static int calculateShippingFeeWon(int orderTotalWon)`을 보면 주문 합계를 입력받아 원 단위 배송비를 계산한다는 내용을 알 수 있다. 이름은 목적, 매개변수는 필요한 입력, 반환 타입은 호출자가 받을 결과의 형태를 설명한다. 메서드 이름과 타입만으로 알기 어려운 전제나 실패 동작은 문서나 테스트로 드러낸다.

Java의 **메서드 선언부**는 코드를 호출할 때 참고하는 정보를 담는다. **메서드 시그니처**는 언어 명세에서 이름, 형식 매개변수 타입, 제네릭 메서드의 타입 매개변수 등을 기준으로 판단하는 용어다. 위 예제의 시그니처는 `calculateShippingFeeWon(int)`다. [Java 메서드 선언](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html#jls-8.4) · [메서드 시그니처](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html#jls-8.4.2)

## 4. 추상화 수준을 맞추고 정책값에 이름 붙이기

다음 코드는 주문 합계가 50,000원 이상이면 무료 배송, 그보다 작으면 3,000원이라는 정책을 담고 있다. 숫자와 이름을 함께 해석해야 조건의 의미가 보인다.

```java
final class ShippingPolicyBefore {
    static int calculate(int amount) {
        return amount >= 50_000 ? 0 : 3_000;
    }
}
```

개선한 코드에서는 `calculateShippingFeeWon`이 무료 배송 여부를 판단해 배송비를 반환한다. 구체적인 비교 기준은 `qualifiesForFreeShipping`에서 확인한다.

```java
final class ShippingPolicy {
    private static final int FREE_SHIPPING_THRESHOLD_WON = 50_000;
    private static final int STANDARD_SHIPPING_FEE_WON = 3_000;

    static int calculateShippingFeeWon(int orderTotalWon) {
        if (qualifiesForFreeShipping(orderTotalWon)) {
            return 0;
        }
        return STANDARD_SHIPPING_FEE_WON;
    }

    private static boolean qualifiesForFreeShipping(int orderTotalWon) {
        return orderTotalWon >= FREE_SHIPPING_THRESHOLD_WON;
    }
}
```

의미를 추측해야 하는 리터럴을 매직 넘버 또는 매직 스트링이라고 부른다. 예제의 50,000과 3,000은 서로 독립적으로 변경될 수 있는 정책값이라 이름을 붙였다. 무료 배송 분기의 `0`은 분기 이름과 반환 단위에서 의미가 바로 드러난다. 조건을 메서드로 추출할 때는 여러 줄을 줄이는 효과보다 호출부에 표현할 개념이 생기는지를 본다.

문자열도 값의 역할에 따라 다룬다. 프로그램이 관리하는 유한한 주문 상태 집합은 `OrderStatus.PAID` 같은 열거형으로 표현할 수 있다. 외부 API나 저장소가 `"PAID"`라는 값을 계약으로 사용한다면 입출력 경계에서 내부 상태로 변환하고, 모르는 값의 처리도 정한다. [Java 열거형](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html#jls-8.9)

## 5. 핵심 키워드로 코드 검토하기

| 키워드 | 리뷰 질문 |
| --- | --- |
| 추상화 수준 | 상위 메서드는 흐름을 설명하고, 하위 메서드는 각 단계의 판단 기준을 보여 주는가? |
| 이름과 메서드 선언부 | 호출부에서 동작과 상태 변경 여부, 입력과 반환값의 단위를 알 수 있는가? |
| 매직 넘버와 매직 스트링 | 숫자나 문자열의 의미가 사용 위치에서 읽히는가? 이름을 붙인 값은 독립적인 정책이나 외부 계약을 나타내는가? |
| 동작 보존 | 구조를 바꾼 뒤에도 경계값의 동작이 같은가? |

배송비 예제에서는 49,999원에 3,000원, 50,000원과 50,001원에 0원이 나와야 한다. [테스트와 리팩터링](../test-driven-development/01_tdd_fundamentals_and_feedback_loops.md)
