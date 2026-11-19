# Readable and Reliable Tests

좋은 테스트는 이름과 준비 데이터, 기대 결과를 읽으면 검증하는 규칙을 설명할 수 있다. 실행 순서나 실행 환경을 바꿔도 같은 조건을 검증하도록 입력과 상태를 제어한다.

## 1. 한 테스트에 규칙 하나 드러내기

한 테스트는 한 시나리오를 설명하도록 이름과 준비 데이터를 고른다. 같은 계약을 확인하는 관련 결과는 함께 단언할 수 있다. 서로 다른 조건에 대한 결과라면 테스트를 나눠 어떤 규칙이 깨졌는지 실패 이름만으로 좁힐 수 있게 한다.

테스트 픽스처는 해당 테스트에서 중요한 값을 가까이 적는다. 예를 들어 마감 시각을 검증한다면 시각과 사용 시간대를 테스트에 드러낸다. 관련 없는 값과 반복 생성 절차는 의도가 보이는 팩터리나 빌더로 줄일 수 있다. 공통 설정을 사용하더라도 해당 테스트가 어느 초기 상태에 기대는지 확인할 수 있어야 한다.

## 2. 환경과 테스트 사이의 상태 제어하기

| 제어할 대상 | 접근 방식 |
| --- | --- |
| 현재 시간, 시간대, 난수 | 필요한 값을 전달하거나, 시간·난수 제공자를 주입해 테스트에서 고정한다. |
| DB, 파일, 큐 | 테스트 전용 환경과 테스트별 데이터 범위를 정한다. 생성한 상태는 롤백, 명시적 삭제 또는 자원 종료로 정리한다. |
| 테스트 사이의 공유 상태 | 테스트마다 새 객체를 만든다. 캐시나 전역 설정을 바꿨다면 다음 테스트가 받을 초기 상태를 복원한다. |

JUnit Jupiter의 기본 수명 주기는 테스트 메서드마다 인스턴스를 새로 만든다. 이 경계 밖에 있는 정적 필드와 DB, 파일, 컨테이너의 상태에는 별도의 격리 방법이 필요하다. `@TempDir`처럼 수명 주기를 관리하는 기능을 쓰거나, 자원을 연 테스트에서 종료까지 책임지게 한다. Spring 테스트의 트랜잭션 롤백은 해당 테스트 트랜잭션에 참여한 변경에 적용된다. 별도 서버 스레드나 별도 트랜잭션의 쓰기는 직접 정리할 방법이 필요하다. [JUnit 테스트 인스턴스 수명 주기](https://docs.junit.org/5.13.4/user-guide/#writing-tests-test-instance-lifecycle) · [Spring TestContext의 트랜잭션 관리](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)

## 3. 반복되는 검증을 테스트 사례로 표현하기

`@ParameterizedTest`는 입력과 기대 결과가 달라지는 여러 사례를 같은 테스트 본문으로 표현할 때 사용한다. 실행 중 사례를 만들어 이름이나 검증 동작을 구성할 때는 `@TestFactory`가 `DynamicTest.dynamicTest(...)`로 만든 테스트를 반환할 수 있다. JUnit Jupiter에서는 `DynamicTest`가 타입이며, 이 방식의 메서드에 붙는 애너테이션은 `@TestFactory`다.

예제는 서울 시간 기준 평일 15:00 이전에 당일 출고한다. 매개변수 테스트는 마감 시각 경계를, 동적 테스트는 요일 사례를 다룬다. 매개변수 테스트에서는 각 호출에 `@BeforeEach`와 `@AfterEach`가 적용된다. 동적 테스트에서는 두 콜백의 실행 단위가 팩터리 메서드이므로, 사례별 픽스처를 실행 람다 안에서 만든다. 예제에는 Java 17과 JUnit Jupiter 5의 API, 엔진, 매개변수 테스트 모듈이 필요하다. [JUnit 매개변수 테스트](https://docs.junit.org/5.13.4/user-guide/#writing-tests-parameterized-tests) · [JUnit 동적 테스트](https://docs.junit.org/5.13.4/user-guide/#writing-tests-dynamic-tests) · [Java SE 17 Clock](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/time/Clock.html)

```java
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.DynamicTest.dynamicTest;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

record ReliableDispatchPolicy(Clock clock) {
    boolean dispatchesToday() {
        ZonedDateTime now = ZonedDateTime.now(clock);
        DayOfWeek day = now.getDayOfWeek();
        return day != DayOfWeek.SATURDAY
                && day != DayOfWeek.SUNDAY
                && now.toLocalTime().isBefore(LocalTime.of(15, 0));
    }
}

class ReliableDispatchPolicyTest {
    private static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");

    @ParameterizedTest(name = "{0}에 당일 출고 가능 여부는 {1}이다")
    @CsvSource({
        "2026-11-20T14:59, true",
        "2026-11-20T15:00, false",
        "2026-11-20T15:01, false"
    })
    void weekdayCutoff(String localDateTime, boolean expected) {
        assertEquals(expected, policyAt(localDateTime).dispatchesToday());
    }

    @TestFactory
    Stream<DynamicTest> dispatchesBeforeCutoffOnWorkingDays() {
        return Stream.of(
                new DayCase("금요일 오전에는 당일 출고한다", "2026-11-20T10:00", true),
                new DayCase("토요일 오전에는 당일 출고를 보류한다", "2026-11-21T10:00", false),
                new DayCase("일요일 오전에는 당일 출고를 보류한다", "2026-11-22T10:00", false)
        ).map(day -> dynamicTest(day.name(), () -> {
            var policy = policyAt(day.localDateTime());
            assertEquals(day.expected(), policy.dispatchesToday());
        }));
    }

    private static ReliableDispatchPolicy policyAt(String localDateTime) {
        var instant = LocalDateTime.parse(localDateTime).atZone(SEOUL).toInstant();
        return new ReliableDispatchPolicy(Clock.fixed(instant, SEOUL));
    }

    private record DayCase(String name, String localDateTime, boolean expected) {}
}
```

## 4. 실행 비용과 공개 계약 다루기

Spring TestContext는 같은 프로세스에서 같은 구성을 쓰는 테스트에 애플리케이션 컨텍스트를 재사용한다. 필요한 구성이 같은 테스트는 프로파일, 테스트 속성, 빈 재정의 구성을 일관되게 두어 시작 비용을 줄인다. 컨텍스트가 재사용되면 테스트 사이의 빈과 외부 데이터 상태도 확인해야 한다. 테스트가 컨텍스트 자체의 상태를 변경했다면 변경 범위에 맞춰 초기화한다. `@DirtiesContext`는 변경된 컨텍스트를 캐시에서 제거해야 하는 경우에 사용한다. [Spring TestContext의 컨텍스트 캐시](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/ctx-management/caching.html)

private 메서드의 판단은 호출자가 관찰하는 공개 동작을 통해 검증한다. 독립적인 정책이 별도 책임을 가진다면 그 개념을 타입으로 빼고 새 계약을 테스트할 수 있다. 테스트 데이터 생성이나 상태 확인을 돕는 전용 메서드는 테스트 소스의 팩터리, 테스트 대역 또는 단언 헬퍼에 둔다. [테스트 시나리오와 API 단언](../test-driven-development/02_test_scenarios_and_api_assertions.md)

## 5. 리뷰할 때 확인할 질문

- 실패 이름에 깨진 규칙이 드러나고, 입력과 기대 결과가 테스트 가까이에 보이는가?
- 시간과 외부 자원을 누구의 수명 주기에서 만들고 정리하는지 분명한가?
- 선택한 테스트 범위와 검증 지점이 공개 계약에 맞는가?
