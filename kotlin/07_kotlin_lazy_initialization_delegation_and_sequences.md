# Kotlin Lazy Initialization, Delegation, and Sequences

`lateinit`은 외부에서 나중에 값을 대입할 때 쓰고, `lazy`는 값을 처음 읽을 때 계산한다. 프로퍼티 위임은 읽기와 쓰기 규칙을 재사용하게 하고, `Sequence`는 컬렉션 연산을 결과가 필요한 시점까지 미룬다. 예제는 Kotlin/JVM과 Java 17을 기준으로 한다.

## 1. `lateinit`과 `lazy`

| 표현 | 초기화 시점 | 읽기와 쓰기 |
| --- | --- | --- |
| `lateinit var` | 설정 코드나 호출자가 명시적으로 값을 대입한다. | nullable 타입과 `Int` 같은 기본형 타입에는 쓸 수 없다. 초기화 전에 읽으면 `UninitializedPropertyAccessException`이 발생하고, 대입 후에도 값을 바꿀 수 있다. |
| `val value by lazy { ... }` | 처음 읽을 때 초기화 블록을 실행한다. | 계산에 성공한 값을 보관하고 이후 읽기에서 재사용한다. `lazy { ... }`는 프로퍼티에 위임하거나 `Lazy<T>.value`로 읽을 수 있다. |

JVM에서 기본 모드인 `SYNCHRONIZED`는 한 스레드가 초기화하도록 동기화한다. `PUBLICATION`은 여러 스레드에서 초기화 블록이 실행될 수 있고 그중 한 결과를 공유한다. `NONE`에는 초기화 동기화가 없으므로 한 스레드에서만 접근하는 경우에 쓴다. [Kotlin · 지연 초기화 프로퍼티](https://kotlinlang.org/docs/properties.html#late-initialized-properties-and-variables) · [Kotlin · `LazyThreadSafetyMode`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-lazy-thread-safety-mode/)

```kotlin
class StockReport {
    lateinit var title: String
    var builds = 0
        private set

    val heading: String by lazy {
        builds++
        title.uppercase()
    }

    fun hasTitle(): Boolean = this::title.isInitialized
}

fun main() {
    val report = StockReport()
    check(!report.hasTitle())
    report.title = "Daily Stock"
    check(report.hasTitle() && report.builds == 0)

    check(report.heading == "DAILY STOCK")
    report.title = "New Title"
    check(report.heading == "DAILY STOCK" && report.builds == 1)
}
```

`heading`처럼 나중에 설정할 값을 참조하는 프로퍼티는 설정이 끝난 뒤 읽어야 한다. 계산한 결과를 보관하므로 이후 `title`을 바꿔도 `heading`을 다시 계산하지 않는다.

## 2. `by lazy`와 프로퍼티 위임

`val name by delegate`로 선언하면 프로퍼티를 읽을 때 `delegate`의 `getValue(thisRef, property)`를 호출한다. `var`의 값을 대입할 때는 `setValue(thisRef, property, value)`도 호출한다. `thisRef`는 프로퍼티를 가진 객체이고 `property`는 이름 등의 메타데이터를 담는다. `by lazy`는 `Lazy<T>`의 `getValue` 연산자를 통해 `value`를 읽는다. 사용자 정의 위임 객체에는 `operator` 함수를 두거나 `ReadOnlyProperty`와 `ReadWriteProperty`를 구현할 수 있다. [Kotlin · 위임 프로퍼티와 위임 객체 요구 사항](https://kotlinlang.org/docs/delegated-properties.html) · [Kotlin · `Lazy<T>.getValue`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/get-value.html)

```kotlin
import kotlin.properties.ReadWriteProperty
import kotlin.reflect.KProperty

class NonNegative(initial: Int) : ReadWriteProperty<Any?, Int> {
    private var current = initial

    init {
        require(initial >= 0)
    }

    override fun getValue(thisRef: Any?, property: KProperty<*>): Int = current

    override fun setValue(thisRef: Any?, property: KProperty<*>, value: Int) {
        require(value >= 0) { "${property.name} must be non-negative" }
        current = value
    }
}

class Inventory {
    var available: Int by NonNegative(0)
}

fun main() {
    val inventory = Inventory()
    inventory.available = 4
    check(runCatching { inventory.available = -1 }.exceptionOrNull() is IllegalArgumentException)
    check(inventory.available == 4)
}
```

## 3. 표준 위임 객체

| 위임 객체 | 시점과 용도 |
| --- | --- |
| `Delegates.notNull<T>()` | 초기값 없이 `var`를 선언하고 나중에 대입한다. 값을 넣기 전 읽으면 `IllegalStateException`이 발생한다. `Int`에도 사용할 수 있다. |
| `Delegates.observable(initial)` | 값이 대입된 뒤 이전 값과 새 값으로 콜백을 호출한다. 변경 기록이나 알림에 쓸 수 있다. |
| `Delegates.vetoable(initial)` | 값이 바뀌기 전에 콜백을 호출한다. 콜백이 `false`를 반환하면 기존 값을 유지한다. |
| `val value by map` | 프로퍼티 이름을 키로 사용한다. `MutableMap`에 위임한 `var`는 같은 키에 새 값을 쓴다. |

[Kotlin · 표준 위임 객체와 맵 위임](https://kotlinlang.org/docs/delegated-properties.html)

```kotlin
import kotlin.properties.Delegates

class StockSettings(values: Map<String, String>) {
    val warehouse: String by values
    val changes = mutableListOf<String>()
    var threshold: Int by Delegates.notNull<Int>()
    var quantity: Int by Delegates.vetoable(0) { _, _, next -> next >= 0 }
    var status: String by Delegates.observable("READY") { _, before, after ->
        changes.add("$before -> $after")
    }
}

fun main() {
    val settings = StockSettings(mapOf("warehouse" to "A1"))
    check(runCatching { settings.threshold }.exceptionOrNull() is IllegalStateException)
    settings.threshold = 2
    settings.quantity = 4
    settings.quantity = -1
    settings.status = "COUNTED"

    check(settings.warehouse == "A1" && settings.threshold == 2)
    check(settings.quantity == 4)
    check(settings.changes == listOf("READY -> COUNTED"))
}
```

## 4. 프로퍼티 연결과 인터페이스 위임

- `var oldName: String by this::newName`으로 이름을 바꾸는 동안 두 프로퍼티가 같은 값을 읽고 쓰게 할 수 있다. `provideDelegate`를 구현하면 프로퍼티가 위임 객체에 연결되는 시점에 프로퍼티 이름이나 설정을 확인할 수 있다. [Kotlin · 다른 프로퍼티에 위임하기](https://kotlinlang.org/docs/delegated-properties.html#delegating-to-another-property) · [Kotlin · 위임 객체 제공](https://kotlinlang.org/docs/delegated-properties.html#providing-a-delegate)
- `class LoggedReader(reader: StockReader) : StockReader by reader`는 재정의하지 않은 인터페이스 호출을 `reader`로 전달한다. 래퍼가 재정의한 메서드는 래퍼를 통해 호출할 때 적용된다. `reader` 내부에서는 `reader`의 구현을 사용한다. [Kotlin · 인터페이스 위임](https://kotlinlang.org/docs/delegation.html)

```kotlin
interface StockReader {
    fun skus(): Set<String>
    fun quantity(sku: String): Int
}

class MapReader(private val stock: Map<String, Int>) : StockReader {
    override fun skus(): Set<String> = stock.keys
    override fun quantity(sku: String): Int = stock[sku] ?: 0
}

class LoggedReader(private val reader: StockReader) : StockReader by reader {
    val lookups = mutableListOf<String>()

    override fun quantity(sku: String): Int {
        lookups.add(sku)
        return reader.quantity(sku)
    }
}

fun main() {
    val reader = LoggedReader(MapReader(mapOf("pen" to 3)))
    check(reader.skus() == setOf("pen"))
    check(reader.quantity("pen") == 3)
    check(reader.lookups == listOf("pen"))
}
```

## 5. `Iterable`과 `Sequence`를 JMH로 비교하기

`Iterable`의 `filter`와 `map`은 단계마다 결과 목록을 만든다. `Sequence`의 중간 연산은 지연되므로 `firstOrNull()`이 값을 찾으면 이후 요소는 평가하지 않는다. 모든 결과를 소비하거나 입력이 작은 경우에는 시퀀스의 반복 비용도 결과에 영향을 준다. [Kotlin · 시퀀스](https://kotlinlang.org/docs/sequences.html)

### 비교할 Kotlin 코드

두 구현은 같은 목록에서 첫 양수의 두 배를 반환한다. 아래 코드를 `StockPipelines.kt`에 둔다.

```kotlin
package bench

fun eagerFirst(stocks: List<Int>): Int? =
    stocks.filter { it > 0 }.map { it * 2 }.firstOrNull()

fun lazyFirst(stocks: List<Int>): Int? =
    stocks.asSequence().filter { it > 0 }.map { it * 2 }.firstOrNull()

fun main() {
    val cases = listOf(emptyList(), listOf(0, 0), listOf(3, 0, 4), listOf(0, 3, 4))
    for (stocks in cases) {
        val expected = stocks.firstOrNull { it > 0 }?.let { it * 2 }
        check(eagerFirst(stocks) == expected && lazyFirst(stocks) == expected)
    }
}
```

### 벤치마크와 실행 방법

`StockBenchmark.java`에서 목록 크기와 첫 일치 위치를 바꾼다. 입력은 `@Setup`에서 만들고, 벤치마크 메서드는 계산 결과를 반환해 JMH가 소비하게 한다. `ns/op`를 비교할 때는 워밍업, 측정 반복, JVM 포크를 확보하고 실행 환경도 함께 기록한다. [OpenJDK · JMH](https://github.com/openjdk/jmh) · [OpenJDK · 결과 소비 예제](https://github.com/openjdk/jmh/blob/master/jmh-samples/src/main/java/org/openjdk/jmh/samples/JMHSample_08_DeadCode.java) · [OpenJDK · 입력 파라미터 예제](https://github.com/openjdk/jmh/blob/master/jmh-samples/src/main/java/org/openjdk/jmh/samples/JMHSample_27_Params.java)

```java
package bench;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
public class StockBenchmark {
    @Param({"100", "10000"})
    public int size;

    @Param({"early", "late"})
    public String match;

    private List<Integer> stocks;

    @Setup
    public void setup() {
        stocks = new ArrayList<>(Collections.nCopies(size, 0));
        stocks.set(match.equals("early") ? 0 : size - 1, 3);
    }

    @Benchmark
    public Integer eager() {
        return StockPipelinesKt.eagerFirst(stocks);
    }

    @Benchmark
    public Integer lazy() {
        return StockPipelinesKt.lazyFirst(stocks);
    }
}
```

두 파일을 같은 실습 폴더에 두고 아래 명령을 실행한다. `KOTLIN_STDLIB`, `JMH_CORE`, `JMH_AP`, `JOPT_SIMPLE`, `COMMONS_MATH3`는 각각 Kotlin 표준 라이브러리와 JMH 1.37의 `jmh-core`, `jmh-generator-annprocess`, `jopt-simple`, `commons-math3` JAR 경로다.

```bash
kotlinc StockPipelines.kt -jvm-target 17 -d out
javac --release 17 -cp "out:$KOTLIN_STDLIB:$JMH_CORE" \
  -processorpath "$JMH_CORE:$JMH_AP" -d out StockBenchmark.java
java -cp "out:$KOTLIN_STDLIB:$JMH_CORE:$JOPT_SIMPLE:$COMMONS_MATH3" \
  org.openjdk.jmh.Main 'bench.StockBenchmark.*' -f 2 -wi 3 -w 1s -i 5 -r 1s
```
