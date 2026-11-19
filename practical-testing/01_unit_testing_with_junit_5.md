# Unit Testing with JUnit 5

단위 테스트는 작게 나눈 동작을 구체적인 입력과 기대 결과로 확인한다. 이 문서에서는 주문 취소 정책을 예로 들어 수동 확인을 반복 가능한 검사로 옮기고, 현재 시각에 따라 결과가 달라지는 로직을 제어한다.

## 1. 수동 확인을 실행 가능한 검사로 옮기기

주문 취소 버튼을 눌러 화면이 바뀌는지 살펴보면 실제 사용 흐름을 관찰할 수 있다. 같은 취소 규칙을 변경할 때마다 다시 확인해야 한다면, 시각과 취소 마감 시각을 입력으로 정하고 결과를 자동으로 비교할 수 있다.

| 방식 | 확인하기 좋은 동작 |
| --- | --- |
| 수동 테스트 | 화면이나 여러 기능이 이어지는 흐름을 탐색하며 새로운 사례를 발견한다. 입력과 관찰한 결과를 남긴다. |
| 자동화된 단위 테스트 | 한 규칙을 여러 입력으로 반복 확인한다. 코드가 기대한 결과를 받았는지 단언으로 판단한다. |

JUnit Jupiter의 `@Test`는 실행할 테스트 메서드를 표시하고, `assertTrue`, `assertFalse`, `assertEquals` 같은 단언이 결과를 확인한다. 테스트 본문에서 준비한 값, 실행한 동작, 검증한 결과를 흐름대로 읽을 수 있게 작성한다. [JUnit 5의 테스트 메서드](https://docs.junit.org/5.13.4/user-guide/#writing-tests-classes-and-methods) · [JUnit 5의 단언](https://docs.junit.org/5.13.4/user-guide/#writing-tests-assertions)

## 2. 정상 입력에서 경계 사례로 넓히기

예제의 주문은 마감 시각 전까지 취소할 수 있다. 먼저 전후의 대표 값을 고른 뒤 비교가 달라지는 경계 자체를 추가한다. 마감과 정확히 같은 시각을 검증하면 `<`과 `<=`의 의미 차이를 드러낼 수 있다.

| 현재 시각 | 취소 가능 여부 |
| --- | --- |
| 마감 1초 전 | 가능 |
| 마감과 같은 시각 | 불가 |
| 마감 1초 후 | 불가 |

이처럼 입력 범위를 나눈 뒤에는 각 사례가 증명하는 규칙을 설명할 수 있어야 한다. 잘못된 입력에 대한 오류 동작도 공개 계약에 포함된다면 별도 사례로 둔다. [테스트 시나리오와 단언](../test-driven-development/02_test_scenarios_and_api_assertions.md)

## 3. 제어하기 어려운 의존을 분리하기

시스템 시각을 직접 읽는 정책은 테스트하는 순간에 따라 결과가 달라질 수 있다. 이 예제는 시각을 얻는 책임을 `Clock`으로 받는다. 실제 호출자는 시스템 시계를, 테스트는 `Clock.fixed`를 전달한다. 세 테스트의 입력 시각은 각각 고정되므로 대기하거나 실행 순서에 기대지 않고 마감의 경계를 확인할 수 있다. [Java 17의 Clock](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/time/Clock.html)

```java
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class UnitCancellationPolicy {
    private final Clock clock;

    UnitCancellationPolicy(Clock clock) {
        this.clock = clock;
    }

    boolean canCancel(Instant deadline) {
        return clock.instant().isBefore(deadline);
    }
}

class UnitCancellationPolicyTest {
    private static final Instant DEADLINE = Instant.parse("2026-11-19T02:00:00Z");

    @Test
    void acceptsCancellationBeforeTheDeadline() {
        var policy = policyAt(DEADLINE.minusSeconds(1));

        assertTrue(policy.canCancel(DEADLINE));
    }

    @Test
    void rejectsCancellationAtTheDeadline() {
        var policy = policyAt(DEADLINE);

        assertFalse(policy.canCancel(DEADLINE));
    }

    @Test
    void rejectsCancellationAfterTheDeadline() {
        var policy = policyAt(DEADLINE.plusSeconds(1));

        assertFalse(policy.canCancel(DEADLINE));
    }

    private static UnitCancellationPolicy policyAt(Instant now) {
        return new UnitCancellationPolicy(Clock.fixed(now, ZoneOffset.UTC));
    }
}
```

난수, 파일, 외부 API처럼 결과를 제어하기 어려운 의존에도 같은 질문을 적용한다. 단위 테스트가 해당 입력을 직접 만들 수 있게 책임을 옮기고, 실제 연결에서만 관찰할 수 있는 동작은 그 연결을 포함한 테스트에서 확인한다.

| 키워드 | 확인할 질문 |
| --- | --- |
| 단위 테스트 | 공개 동작 하나를 짧은 입력과 단언으로 확인하는가? |
| 사례 세분화 | 대표 입력, 경계값, 계약에 있는 예외가 드러나는가? |
| 의존 제어 | 실행 시각과 외부 상태를 입력처럼 준비할 수 있는가? |
