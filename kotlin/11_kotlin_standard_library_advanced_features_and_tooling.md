# Kotlin Standard Library, Advanced Features, and Tooling

컬렉션을 만드는 표준 함수와 입력을 확인하는 함수는 반복되는 코드의 의도를 드러낸다. 꼬리 재귀, 값 클래스, 여러 예외를 처리하는 방법은 각각 반복 실행, 값의 타입 구분, 실패 처리에 쓰인다. 각 예제는 Kotlin/JVM에서 별도 파일로 실행할 수 있다.

## 1. 활용도 높은 표준 라이브러리 함수

| 함수 | 쓰는 경우 |
| --- | --- |
| `buildList { ... }` | 조건에 따라 항목을 추가하고 호출자에게 읽기 전용 리스트를 반환한다. |
| `groupingBy(selector).eachCount()` | 그룹별 목록 대신 그룹마다 몇 개 있는지만 구할 때 쓴다. |
| `mutableMap.getOrPut(key) { ... }` | 키의 값이 없거나 `null`일 때 초기값을 계산해 저장한다. |
| `chunked(size)` | 자료를 겹치지 않는 묶음으로 나눈다. 마지막 묶음은 더 작을 수 있다. |
| `windowed(size)` | 기본 간격 1로 이동하면서 연속된 구간을 만든다. 인접한 값의 관계를 볼 때 쓴다. |
| `require(condition)` / `check(condition)` | 입력이나 호출 전제는 `require`, 현재 상태는 `check`로 확인한다. 조건이 거짓이면 각각 `IllegalArgumentException`, `IllegalStateException`이 발생한다. |

[Kotlin · `buildList`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/build-list.html) · [Kotlin · 그룹별 집계](https://kotlinlang.org/docs/collection-grouping.html) · [Kotlin · `getOrPut`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/get-or-put.html) · [Kotlin · 컬렉션 구간](https://kotlinlang.org/docs/collection-parts.html) · [Kotlin · 사전 조건 검사](https://kotlinlang.org/docs/exceptions.html)

```kotlin
fun main() {
    val restockNeeded = true
    val tasks = buildList {
        add("count")
        if (restockNeeded) add("reorder")
    }
    val scanned = listOf("pen", "notebook", "pen")
    val counts = scanned.groupingBy { it }.eachCount()

    val scansByShelf = mutableMapOf<String, MutableList<String>>()
    scansByShelf.getOrPut("A1") { mutableListOf() }.add("pen")

    check(tasks == listOf("count", "reorder"))
    check(counts == mapOf("pen" to 2, "notebook" to 1))
    check(scansByShelf["A1"] == listOf("pen"))
    check(scanned.chunked(2) == listOf(listOf("pen", "notebook"), listOf("pen")))
    check(scanned.windowed(2) == listOf(listOf("pen", "notebook"), listOf("notebook", "pen")))
}
```

## 2. 꼬리 재귀, 값 클래스, 여러 예외 처리

### `tailrec`으로 재귀 호출을 반복문으로 바꾸기

재귀 호출의 결과가 해당 실행 경로의 최종 결과라면 꼬리 위치에 있다. `tailrec` 조건을 충족하면 Kotlin 컴파일러가 자체 호출을 반복문으로 바꿔 스택 프레임을 쌓지 않는다. `n + sumTo(n - 1)`은 호출이 끝난 뒤 덧셈이 남으므로, 아래와 같이 누적값을 다음 호출에 넘긴다. `open` 함수나 `try`·`catch`·`finally` 안의 재귀 호출에는 이 최적화를 적용할 수 없다. [Kotlin · 꼬리 재귀 함수](https://kotlinlang.org/docs/functions.html#tail-recursive-functions)

```kotlin
tailrec fun sumTo(n: Long, accumulated: Long = 0): Long =
    if (n <= 0) accumulated else sumTo(n - 1, accumulated + n)

fun main() {
    check(sumTo(0) == 0L)
    check(sumTo(5) == 15L)
    check(sumTo(100_000) == 5_000_050_000L)
}
```

### JVM 값 클래스로 같은 기본 타입의 의미 구분하기

`@JvmInline value class`는 기반 값을 감싸는 별도 Kotlin 타입을 정의한다. `ProductId`와 `WarehouseId`가 모두 `String`에 기반해도 컴파일러는 두 타입을 구분한다. `typealias ProductId = String`의 별칭은 그대로 `String`으로 취급된다. JVM은 가능하면 기반 값으로 표현하며, 제네릭이나 인터페이스 등 다른 타입으로 사용할 때는 래퍼가 필요할 수 있다. [Kotlin · 인라인 값 클래스](https://kotlinlang.org/docs/inline-classes.html) · [Kotlin · 타입 별칭](https://kotlinlang.org/docs/type-aliases.html)

```kotlin
@JvmInline
value class ProductId(val value: String) {
    init {
        require(value.isNotBlank()) { "Product ID is required" }
    }
}

@JvmInline
value class WarehouseId(val value: String)

fun stockKey(product: ProductId, warehouse: WarehouseId): String =
    "${warehouse.value}/${product.value}"

fun main() {
    check(stockKey(ProductId("pen"), WarehouseId("A1")) == "A1/pen")
    check(runCatching { ProductId(" ") }.exceptionOrNull() is IllegalArgumentException)
}
```

### 여러 예외를 각각 처리하기

Kotlin에서는 Java의 `catch (A | B e)`에 해당하는 타입을 `catch` 블록별로 적는다. 처음 일치하는 블록이 실행되므로 상위 타입보다 구체적인 예외를 먼저 처리한다. 여러 실패가 같은 맥락에서 처리되더라도, 입력 오류만 복구해야 한다면 잡을 예외의 범위를 입력 오류로 제한한다. [Kotlin · 여러 `catch` 블록](https://kotlinlang.org/docs/exceptions.html)

```kotlin
import java.time.LocalDate
import java.time.format.DateTimeParseException

data class Movement(val quantity: Int, val date: LocalDate)

fun parseMovement(quantity: String, date: String): Movement? = try {
    Movement(quantity.toInt(), LocalDate.parse(date))
} catch (_: NumberFormatException) {
    null
} catch (_: DateTimeParseException) {
    null
}

fun main() {
    check(parseMovement("3", "2024-02-29") == Movement(3, LocalDate.of(2024, 2, 29)))
    check(parseMovement("three", "2024-02-29") == null)
    check(parseMovement("3", "2023-02-29") == null)
}
```

## 3. Kotlin 프로젝트의 대표 도구

| 도구 | 맡기는 작업 |
| --- | --- |
| ktlint | 코드 스타일 규칙을 검사하고, 자동 수정할 수 있는 포맷 문제를 고친다. [ktlint · 공식 저장소](https://github.com/ktlint/ktlint) |
| detekt | 복잡한 함수나 문제가 될 수 있는 패턴을 정적 분석 규칙으로 찾는다. [detekt · 공식 문서](https://detekt.dev/docs/intro/) |
| Kotest | Kotlin 테스트 명세와 단언을 작성하고, 여러 입력에서 성립해야 하는 속성을 검증한다. [Kotest · 공식 문서](https://kotest.io/docs/quickstart/) |
| MockK | 테스트 대역의 반환값을 지정하고, 의존성에 의도한 호출이 전달됐는지 검증한다. [MockK · 공식 문서](https://mockk.io/) |
