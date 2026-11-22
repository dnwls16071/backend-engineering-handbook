# Testing PaymentService with a Fixed Exchange Rate

PaymentService의 계산 규칙을 검증할 때 고정 환율을 주입한다. 예제는 미화 2단위에 1단위당 1,300원의 환율을 적용한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Java 21 BigDecimal](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html)

## 1. 외부 호출과 계산을 분리해 검증한다

```java
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class PaymentServiceTest {
    interface ExRateProvider {
        BigDecimal usdToKrw();
    }

    record PaymentService(ExRateProvider rates) {
        BigDecimal prepare(BigDecimal usd) {
            return usd.multiply(rates.usdToKrw());
        }
    }

    @Test
    void convertsUsdUsingTheGivenRate() {
        var service = new PaymentService(() -> new BigDecimal("1300"));
        assertEquals(new BigDecimal("2600"), service.prepare(new BigDecimal("2")));
    }
}
```

외부 HTTP의 실제 응답 규약은 별도 어댑터 테스트에서 검증한다. 실서비스에서 반올림이 필요하면 통화 규칙을 명시하고, 수치 값만 비교할지 스케일도 계약으로 볼지 정한다. [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) · [Java 21 BigDecimal](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)

## 2. 업무 경계에서 실패도 검증한다

환율 조회 실패를 앱 예외로 바꾸는 규칙이 있다면 조회 대역이 실패하도록 만든다. 기대한 오류가 전달되고 결제 준비가 성공으로 기록되지 않는지 확인한다. [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)
