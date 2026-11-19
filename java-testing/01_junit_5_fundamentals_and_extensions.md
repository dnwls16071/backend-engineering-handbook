# JUnit 5 Fundamentals and Extensions

JUnit 5에서 테스트를 작성하고 실행할 때는 Jupiter의 애너테이션과 단언을 사용한다. 테스트가 실행되는 조건, 반복할 입력, 테스트 인스턴스의 수명, 공통 동작을 등록하는 방법도 함께 정할 수 있다. 실습 기준은 **Java 17과 JUnit 5.12.2**다.

## 1. JUnit 5 구성과 첫 테스트

| 구성 | 역할 |
| --- | --- |
| JUnit Platform | 테스트 엔진을 발견하고 실행한다. Gradle, Maven, IDE가 사용할 실행 기반을 제공한다. |
| JUnit Jupiter | JUnit 5 테스트와 확장을 작성하는 API와 그 테스트를 실행하는 엔진을 제공한다. |
| JUnit Vintage | JUnit 3·4 테스트를 JUnit Platform에서 실행할 때 사용한다. 기존 테스트의 점진적 전환에 쓸 수 있다. |

Gradle Java 프로젝트에서는 다음 의존성을 테스트 범위에 둔다. BOM은 Jupiter와 Platform 모듈 버전을 맞춘다. Java 예제는 `src/test/java`에 클래스별로 둔다. [JUnit 5 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Gradle에서 JUnit Platform 사용](https://docs.junit.org/5.12.2/user-guide/#running-tests-build-gradle)

```groovy
dependencies {
    testImplementation platform('org.junit:junit-bom:5.12.2')
    testImplementation 'org.junit.jupiter:junit-jupiter'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}

tasks.named('test', Test) {
    useJUnitPlatform()
}
```

## 2. 테스트 이름과 단언

`@DisplayName`은 실행 보고서에 표시할 이름을 지정한다. 여러 테스트에 같은 이름 규칙을 적용하려면 클래스에 `@DisplayNameGeneration`을 둔다. 표시 이름은 개별 `@DisplayName`, 클래스에서 지정한 생성기, 전역 기본 생성기 순으로 결정된다. [Display Names](https://docs.junit.org/5.12.2/user-guide/#writing-tests-display-names)

```java
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class QuantityTest {
    @Test
    @DisplayName("두 상품 묶음의 수량을 합산한다")
    void addsQuantities() {
        int total = positiveQuantity(2) + positiveQuantity(3);

        assertAll(
                () -> assertEquals(5, total),
                () -> assertEquals(1, positiveQuantity(1))
        );
    }

    @Test
    @DisplayName("수량이 0이면 입력을 거부한다")
    void rejectsZero() {
        var error = assertThrows(IllegalArgumentException.class, () -> positiveQuantity(0));

        assertEquals("Quantity must be positive", error.getMessage());
    }

    private static int positiveQuantity(int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("Quantity must be positive");
        }
        return quantity;
    }
}
```

`assertEquals`는 기대값, 실제값, 실패 메시지 순으로 받는다. `assertAll`은 서로 독립적인 검사를 함께 실행해 여러 실패를 한 번에 보고한다. `assertThrows`는 지정 타입과 하위 타입을 허용하고 예외 인스턴스를 반환한다. 정확한 예외 타입이 계약에 포함되면 `assertThrowsExactly`를 사용한다. 시간 제한을 검증하는 `assertTimeout`은 같은 스레드에서 실행한다. `assertTimeoutPreemptively`는 별도 스레드에서 실행하므로 트랜잭션처럼 스레드에 묶인 컨텍스트가 필요한 코드에서는 이를 고려한다. [Assertions](https://docs.junit.org/5.12.2/user-guide/#writing-tests-assertions)

## 3. 실행 조건과 가정

`@EnabledOnOs`, `@EnabledOnJre`, `@EnabledIfSystemProperty`와 대응하는 비활성화 애너테이션은 실행 환경을 기준으로 테스트 실행 여부를 결정한다. `@Disabled`에는 비활성화 이유를 적을 수 있다. 반면 `Assumptions.assumeTrue`는 테스트 본문에서 전제 조건을 확인한다. 전제가 충족되지 않으면 실행이 중단(aborted)되며, 단언 실패와는 별도로 집계된다. [Assumptions](https://docs.junit.org/5.12.2/user-guide/#writing-tests-assumptions) · [Conditional Test Execution](https://docs.junit.org/5.12.2/user-guide/#writing-tests-conditional-execution)

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class ExecutionConditionTest {
    @Test
    @EnabledIfSystemProperty(named = "demo.conditional", matches = "true")
    void runsWhenEnabled() {
        assertEquals(10, Integer.parseInt("10"));
    }

    @Test
    void runsWhenFixtureIsAvailable() {
        assumeTrue(Boolean.getBoolean("demo.fixture.available"), "fixture is required");

        assertEquals(10, Integer.parseInt("10"));
    }
}
```

두 시스템 속성을 지정하지 않으면 첫 테스트는 비활성화되고 두 번째 테스트는 전제에서 중단된다. 각각의 속성을 `true`로 설정하면 두 테스트 모두 본문의 단언을 실행한다.

## 4. 태그, 실행 필터, 커스텀 애너테이션

`@Tag("fast")`처럼 테스트 그룹을 표현하고 빌드 도구에서 포함하거나 제외할 수 있다. 같은 태그를 반복해서 붙일 때는 `@Test`와 `@Tag`를 하나의 합성 애너테이션으로 묶는다. 클래스 전체를 분류하려면 클래스에 `@Tag`를 붙일 수 있다. [Tagging and Filtering](https://docs.junit.org/5.12.2/user-guide/#writing-tests-tagging-and-filtering) · [Meta-Annotations and Composed Annotations](https://docs.junit.org/5.12.2/user-guide/#writing-tests-meta-annotations)

```java
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Tag("fast")
@Test
@interface FastTest {
}

class TaggedQuantityTest {
    @FastTest
    void acceptsPositiveQuantity() {
        assertTrue(Integer.parseInt("3") > 0);
    }
}
```

빠른 테스트만 실행하려면 Gradle의 해당 테스트 작업에 필터를 둔다. 전체 검증에서도 같은 작업을 쓴다면 별도 작업을 두거나, 실행 목적에 따라 필터를 선택할 수 있다.

```groovy
tasks.named('test', Test) {
    useJUnitPlatform {
        includeTags 'fast'
    }
}
```

## 5. 반복 테스트와 매개변수화 테스트

`@RepeatedTest`는 같은 테스트를 여러 번 실행하며 각 반복에 일반 테스트와 같은 생명주기 콜백을 적용한다. `@ParameterizedTest`는 다른 입력이나 기대 결과로 같은 규칙을 검사한다. 한 종류의 값은 `@ValueSource`, 여러 열의 값은 `@CsvSource`, 복합 객체는 `@MethodSource`로 전달할 수 있다. [Repeated Tests](https://docs.junit.org/5.12.2/user-guide/#writing-tests-repeated-tests) · [Parameterized Tests](https://docs.junit.org/5.12.2/user-guide/#writing-tests-parameterized-tests)

```java
import java.util.Locale;

import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RepeatAndParametersTest {
    @RepeatedTest(value = 3, name = "{displayName} [{currentRepetition}/{totalRepetitions}]")
    void normalizesTheSameInput() {
        assertEquals("READY", normalize(" ready "));
    }

    @ParameterizedTest(name = "[{index}] {0} becomes {1}")
    @CsvSource({"ready, READY", "' in progress ', IN PROGRESS", "'', ''"})
    void normalizesEachInput(String input, String expected) {
        assertEquals(expected, normalize(input));
    }

    private static String normalize(String input) {
        return input.trim().toUpperCase(Locale.ROOT);
    }
}
```

## 6. 테스트 인스턴스, 실행 순서, 전역 설정

| 항목 | 동작 |
| --- | --- |
| `PER_METHOD` | Jupiter의 기본값이다. 각 테스트 실행에 새 인스턴스를 만든다. |
| `PER_CLASS` | 클래스의 테스트가 인스턴스를 공유한다. 인스턴스 메서드로 `@BeforeAll`과 `@AfterAll`을 작성할 수 있다. 공유 가변 상태는 `@BeforeEach`에서 초기화하는 등 명시적으로 관리한다. |
| 실행 순서 | 기본 순서는 결정적이지만 메서드 선언 순서에 의존할 수 없다. 명시적 순서가 필요한 시나리오는 `@TestMethodOrder(MethodOrderer.OrderAnnotation.class)`와 `@Order`로 표현한다. |

단위 테스트는 개별 실행에서도 같은 결과가 나도록 만든다. 여러 단계의 상태가 앞 단계에 의존하는 하나의 시나리오는 테스트를 여러 메서드로 쪼개고 순서로 묶기보다 한 테스트 안에서 단계로 표현할 수 있다. [Test Instance Lifecycle](https://docs.junit.org/5.12.2/user-guide/#writing-tests-test-instance-lifecycle) · [Test Execution Order](https://docs.junit.org/5.12.2/user-guide/#writing-tests-test-execution-order)

일반적인 Java 프로젝트에서 `src/test/resources/junit-platform.properties`를 두면 테스트 클래스패스의 루트에서 설정을 읽는다. 프로젝트 전체 기본값은 파일에 두고, 특정 클래스에서만 필요한 생명주기와 순서는 그 클래스에 선언한다. [Configuration Parameters](https://docs.junit.org/5.12.2/user-guide/#running-tests-config-params)

```properties
junit.jupiter.testinstance.lifecycle.default=per_method
junit.jupiter.displayname.generator.default=org.junit.jupiter.api.DisplayNameGenerator$ReplaceUnderscores
```

## 7. Jupiter 확장 모델

`BeforeEachCallback`은 테스트 실행 전에 공통 동작을 실행할 수 있고, `ParameterResolver`는 테스트나 생명주기 메서드의 매개변수에 값을 공급할 수 있다. `@ExtendWith`는 확장을 선언적으로 등록한다. 생성자 인자 등으로 직접 구성한 확장 인스턴스는 `@RegisterExtension` 필드로 등록할 수 있다. 아래 예제는 테스트마다 고정된 시계를 제공한다. [Extension Model](https://docs.junit.org/5.12.2/user-guide/#extensions)

```java
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.extension.ExtensionContext;
import org.junit.jupiter.api.extension.ParameterContext;
import org.junit.jupiter.api.extension.ParameterResolver;

import static org.junit.jupiter.api.Assertions.assertEquals;

@ExtendWith(FixedClockExtension.class)
class FixedClockTest {
    @Test
    void receivesFixedTime(Clock clock) {
        assertEquals(Instant.parse("2025-03-01T09:00:00Z"), clock.instant());
    }
}

class FixedClockExtension implements ParameterResolver {
    @Override
    public boolean supportsParameter(ParameterContext parameter, ExtensionContext context) {
        return parameter.getParameter().getType() == Clock.class;
    }

    @Override
    public Object resolveParameter(ParameterContext parameter, ExtensionContext context) {
        return Clock.fixed(Instant.parse("2025-03-01T09:00:00Z"), ZoneOffset.UTC);
    }
}
```

## 8. JUnit 4에서 점진적으로 전환

같은 프로젝트에서 JUnit 4와 Jupiter 테스트가 공존해야 할 때는 JUnit 4 의존성과 Vintage 엔진을 함께 둘 수 있다. 새 테스트는 Jupiter로 작성하고 기존 테스트를 옮길 때 애너테이션, 단언의 인자 순서, 초기화 범위를 확인한다. 전환 후 실행된 테스트 목록을 비교하면 발견되지 않은 기존 테스트를 찾는 데 도움이 된다. [Migrating from JUnit 4](https://docs.junit.org/5.12.2/user-guide/#migrating-from-junit4)

| JUnit 4 | JUnit Jupiter |
| --- | --- |
| `org.junit.Test` | `org.junit.jupiter.api.Test` |
| `@Before` / `@After` | `@BeforeEach` / `@AfterEach` |
| `@BeforeClass` / `@AfterClass` | `@BeforeAll` / `@AfterAll` |
| `@Ignore` / `@Category` | `@Disabled` / `@Tag` |
| `@Test(expected = ...)` | `assertThrows` |
| `@Test(timeout = ...)` | `@Timeout` 또는 `assertTimeout`. 스레드와 타임아웃 동작을 확인한다. |
| `@RunWith`, `@Rule`, `@ClassRule` | 용도에 따라 `@ExtendWith`, `@RegisterExtension`, `@TempDir` 등으로 전환한다. |

실제 테스트의 경계값과 제어하기 어려운 의존을 다루는 예제는 [Unit Testing with JUnit 5](../practical-testing/01_unit_testing_with_junit_5.md)에 이어진다.
