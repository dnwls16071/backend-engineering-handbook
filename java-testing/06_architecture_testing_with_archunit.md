# Architecture Testing with ArchUnit

ArchUnit은 컴파일된 Java 클래스를 읽어 패키지 경계와 클래스 간 의존성을 검증한다. 이 문서에서는 주문 조회 예제로 도메인이 웹·저장소 구현을 참조하지 않고, 웹 코드가 저장소 인터페이스에 의존하는지 확인한다. 실습 기준은 **Java 17, JUnit 5.12.2, ArchUnit 1.4.1**이다. [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html) · [ArchUnit 1.4.1 Release](https://github.com/TNG/ArchUnit/releases/tag/v1.4.1)

## 1. 의존성 추가

[JUnit 5 문서](01_junit_5_fundamentals_and_extensions.md)의 Gradle 테스트 설정에 아래 의존성을 추가한다. `archunit-junit5`는 규칙을 선언하는 API와 JUnit Platform에서 규칙을 발견하고 실행하는 엔진을 함께 제공한다. 기존 테스트 작업의 `useJUnitPlatform()` 설정을 사용한다. [ArchUnit Installation](https://www.archunit.org/userguide/html/000_Index.html#_installation)

```groovy
dependencies {
    testImplementation 'com.tngtech.archunit:archunit-junit5:1.4.1'
}
```

## 2. 예제의 패키지와 클래스

| 패키지 | 클래스 | 설계 의도 |
| --- | --- | --- |
| `example.orders.domain` | `OrderStore` | 주문 상태를 읽는 인터페이스를 정의한다. |
| `example.orders.persistence` | `MapOrderStore` | 메모리 Map으로 인터페이스를 구현한다. |
| `example.orders.web` | `OrderEndpoint` | 생성자에서 인터페이스를 받아 주문 상태를 반환한다. |

각 코드를 `src/main/java`의 패키지 경로에 클래스명과 같은 파일명으로 둔다.

```java
package example.orders.domain;

import java.util.Optional;

public interface OrderStore {
    Optional<String> findStatus(String orderId);
}
```

```java
package example.orders.persistence;

import java.util.Map;
import java.util.Optional;

import example.orders.domain.OrderStore;

public final class MapOrderStore implements OrderStore {
    private final Map<String, String> statuses;

    public MapOrderStore(Map<String, String> statuses) {
        this.statuses = Map.copyOf(statuses);
    }

    @Override
    public Optional<String> findStatus(String orderId) {
        return Optional.ofNullable(statuses.get(orderId));
    }
}
```

```java
package example.orders.web;

import example.orders.domain.OrderStore;

public final class OrderEndpoint {
    private final OrderStore store;

    public OrderEndpoint(OrderStore store) {
        this.store = store;
    }

    public String status(String orderId) {
        return store.findStatus(orderId).orElse("UNKNOWN");
    }
}
```

## 3. JUnit 5에서 의존성 규칙 실행

`@AnalyzeClasses`로 분석할 애플리케이션 패키지를 정하고 `DoNotIncludeTests`로 테스트 출력물을 제외한다. `@ArchTest`를 붙인 `ArchRule` 필드가 JUnit Platform의 실행 대상이 된다. 아래 테스트는 `src/test/java/example/architecture/OrderArchitectureTest.java`에 둔다. [ArchUnit JUnit Integration](https://www.archunit.org/userguide/html/000_Index.html#_junit_integration)

```java
package example.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import example.orders.persistence.MapOrderStore;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

@AnalyzeClasses(
        packages = "example.orders",
        importOptions = ImportOption.DoNotIncludeTests.class
)
class OrderArchitectureTest {
    @ArchTest
    static final ArchRule domainDoesNotDependOnAdapters = noClasses()
            .that().resideInAPackage("example.orders.domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                    "example.orders.web..", "example.orders.persistence..")
            .because("the domain defines the contract used by its adapters");

    @ArchTest
    static final ArchRule webDoesNotDependOnTheMapStore = noClasses()
            .that().resideInAPackage("example.orders.web..")
            .should().dependOnClassesThat()
            .haveFullyQualifiedName(MapOrderStore.class.getName())
            .because("web code uses the OrderStore interface");
}
```

첫 규칙은 도메인 클래스에서 웹이나 저장소 패키지로 향하는 의존성을 검사한다. 패키지 패턴의 끝에 붙은 `..`는 해당 패키지와 하위 패키지를 포함한다. 두 번째 규칙은 웹 클래스가 `MapOrderStore` 구현에 직접 의존하는지 확인한다. 필드나 생성자 서명에 구현 타입을 사용해도 의존성으로 잡힌다. [ArchUnit Use Cases](https://www.archunit.org/use-cases) · [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)

## 4. 규칙이 위반을 발견하는지 확인

`./gradlew test`로 두 규칙이 통과하는지 확인한 뒤, 다음 변경을 한 번에 하나씩 적용해 실패 메시지를 읽고 되돌린다.

| 실험 | 기대 결과 |
| --- | --- |
| `OrderStore`에 기본 메서드 `default example.orders.web.OrderEndpoint endpoint() { return new example.orders.web.OrderEndpoint(this); }`를 추가한다. | 도메인이 웹 타입을 참조하므로 패키지 규칙이 실패한다. |
| `OrderEndpoint` 생성자 매개변수 타입을 `OrderStore`에서 `MapOrderStore`로 바꾼다. | 웹에서 저장소 구현을 직접 참조하므로 클래스 규칙이 실패한다. |

의존성 위반 메시지에서 출발 클래스, 대상 클래스, 의존성이 발견된 위치를 확인한다. ArchUnit의 정적 분석은 직접 의존성을 드러낸다. 런타임 설정이나 리플렉션으로 어떤 구현이 연결되는지는 [Spring 통합 테스트](03_integration_testing_with_testcontainers_and_docker_compose.md)에서 별도로 확인할 수 있다. [ArchUnit Core API](https://www.archunit.org/userguide/html/000_Index.html#_the_core_api)
