# Writing JUnit Jupiter Tests

JUnit Jupiter에서 @Test로 검사 메서드를 지정하고 Assertions로 동작을 단언한다. 기대값과 실제값의 순서는 assertEquals(expected, actual)이다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 1. 값과 예외를 단언한다

```java
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class QuotientTest {
    static int divide(int dividend, int divisor) {
        return dividend / divisor;
    }

    @Test
    void dividesIntegers() {
        assertEquals(5, divide(10, 2));
    }

    @Test
    void rejectsZeroDivisor() {
        assertThrows(ArithmeticException.class, () -> divide(10, 0));
    }
}
```

예외 테스트의 람다에는 검사하려는 호출만 넣는다. 같은 검증을 여러 입력에 적용하려면 @ParameterizedTest와 입력 공급자를 검토한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 2. 테스트 인스턴스의 수명을 확인한다

JUnit Jupiter의 기본 PER_METHOD는 테스트 메서드마다 새 인스턴스를 만든다. 필요한 준비를 @BeforeEach에 둘 수 있으며, 외부 저장소나 static 상태는 별도로 격리한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)
