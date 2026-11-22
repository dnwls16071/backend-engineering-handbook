# Testing Time with Clock

현재 시간이 업무 규칙에 들어오면 Clock을 받아 시간을 하나의 의존성으로 둔다. 예제에서는 만료 시각과 같아지는 순간부터 결제 견적을 사용할 수 없다고 정한다. [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) · [Java 21 Instant](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Instant.html)

## 1. 고정 시각으로 경계를 검증한다

```java
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QuoteExpiryTest {
    static boolean expired(Instant deadline, Clock clock) {
        return !Instant.now(clock).isBefore(deadline);
    }

    @Test
    void expiresAtTheBoundary() {
        var deadline = Instant.parse("2026-01-01T00:30:00Z");
        assertFalse(expired(deadline, Clock.fixed(deadline.minusSeconds(1), ZoneOffset.UTC)));
        assertTrue(expired(deadline, Clock.fixed(deadline, ZoneOffset.UTC)));
    }
}
```

기한 계산이 Instant 기준이라면 현지 시간대를 업무 날짜와 혼합하지 않는다. 현지 자정이나 영업일이 규칙이라면 ZoneId를 계약에 포함하고 시간대 경계를 별도로 검사한다. [Java 21 Instant](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Instant.html) · [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 2. 실행 환경의 시간 소스를 구성한다

일반 실행에는 시스템 시계로 구성한 Clock을 주입하고, 테스트는 Clock.fixed를 쓴다. 테스트에서 실제 시간이 흐를 때까지 기다리는 작업을 줄인다. [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)
