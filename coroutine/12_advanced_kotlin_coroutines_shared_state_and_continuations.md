# Advanced Kotlin Coroutines: Shared State, Start Options, and Continuations

여러 코루틴이 같은 값을 갱신할 때는 스레드 수와 중단 지점을 함께 고려해야 한다. 공유 상태의 보호 방법을 비교한 뒤 코루틴의 시작 옵션, `Dispatchers.Unconfined`, `Continuation`으로 재개되는 과정을 살펴본다. 예제는 Java 17과 [01번의 `kotlinx-coroutines-core` 1.10.2 설정](01_kotlin_coroutine_fundamentals_jobs_and_cancellation.md)을 사용한다.

## 1. 공유 상태와 경쟁 상태

`counter++`는 기존 값 읽기, 더하기, 새 값 쓰기로 구성된다. 두 스레드가 기존 값을 동시에 읽으면 같은 결과를 써서 갱신 하나가 사라질 수 있다. 한 스레드를 써도 공유 값을 읽은 뒤 중단되고, 다른 코루틴이 값을 읽거나 갱신하면 같은 문제가 생길 수 있다. `@Volatile`은 읽기와 쓰기의 가시성을 제공하지만 복합 연산 전체를 원자적으로 만들지는 않는다. [Kotlin · 공유 가변 상태와 동시성](https://kotlinlang.org/docs/shared-mutable-state-and-concurrency.html)

| 보호 방법 | 적용할 때 |
| --- | --- |
| 공유 가변 상태 줄이기 | 각 작업이 결과를 반환하고 한 곳에서 합칠 수 있을 때 |
| 상태의 소유 범위 제한 | 한 코루틴이 변경 요청을 받아 상태를 갱신하게 할 때 |
| `Mutex.withLock` | 여러 읽기와 쓰기가 한 임계 구역 안에서 수행되어야 할 때 |
| 원자 자료구조 | 카운터처럼 한 값에 대한 연산을 원자적으로 수행할 수 있을 때 |

아래에서는 두 작업 모두 기존 값을 읽은 뒤에만 쓰기 신호를 보내 갱신 유실을 재현한다. 두 번째 계산에서는 같은 `Mutex`로 읽기와 쓰기를 묶는다. 다른 코루틴이 락을 가지고 있으면 `Mutex`는 락을 기다리는 코루틴을 중단할 수 있다. [kotlinx.coroutines · `Mutex`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.sync/-mutex/) · [kotlinx.coroutines · `withLock`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.sync/with-lock.html)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.joinAll
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

fun main() = runBlocking {
    var unsafeCount = 0
    val read = List(2) { CompletableDeferred<Unit>() }
    val write = CompletableDeferred<Unit>()
    val racing = read.map { signal ->
        launch {
            val snapshot = unsafeCount
            signal.complete(Unit)
            write.await()
            unsafeCount = snapshot + 1
        }
    }
    read.forEach { it.await() }
    write.complete(Unit)
    racing.joinAll()
    check(unsafeCount == 1)

    var safeCount = 0
    val mutex = Mutex()
    List(100) {
        launch(Dispatchers.Default) {
            mutex.withLock { safeCount++ }
        }
    }.joinAll()
    check(safeCount == 100)
}
```

## 2. 원자 자료구조로 갱신 유실 막기

JVM의 `AtomicInteger`는 `incrementAndGet()`이나 `compareAndSet(expected, updated)` 같은 원자 연산을 제공한다. 아래 재고 차감에서는 현재 수량을 읽고, 그 값이 여전히 같을 때만 차감한다. 다른 작업이 먼저 수량을 바꾸면 최신 값으로 다시 시도한다. 여러 필드를 함께 검증하고 갱신해야 한다면 한 임계 구역에서 상태 전체를 보호할 수 있다. [Java 17 · `AtomicInteger`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html) · [Kotlin · 원자 자료구조](https://kotlinlang.org/docs/shared-mutable-state-and-concurrency.html)

```kotlin
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking

class Stock(initial: Int) {
    private val remaining = AtomicInteger(initial)

    init {
        require(initial >= 0)
    }

    fun reserve(quantity: Int): Boolean {
        require(quantity > 0)
        while (true) {
            val snapshot = remaining.get()
            if (snapshot < quantity) return false
            if (remaining.compareAndSet(snapshot, snapshot - quantity)) return true
        }
    }

    fun remaining(): Int = remaining.get()
}

fun main() = runBlocking {
    val stock = Stock(initial = 40)
    val reservations = List(100) {
        async(Dispatchers.Default) { stock.reserve(1) }
    }.awaitAll()

    check(reservations.count { it } == 40)
    check(stock.remaining() == 0)
}
```

## 3. `CoroutineStart`의 실행 옵션

| 옵션 | 시작 방식 |
| --- | --- |
| `DEFAULT` | 설정된 디스패처 정책에 따라 실행을 예약한다. 본문에 들어가기 전에 취소되면 본문이 실행되지 않을 수 있다. |
| `LAZY` | `start()`나 `join()`을 호출할 때까지 시작을 미룬다. `async`로 만든 작업은 `await()`로도 시작할 수 있다. |
| `ATOMIC` | 본문에 들어가기 전 취소로 시작이 생략되는 것을 막는다. 시작한 뒤에는 취소를 지원하는 중단 지점에서 취소를 감지한다. |
| `UNDISPATCHED` | 첫 실제 중단 지점까지 호출 스레드에서 즉시 실행한다. 이후 작업은 설정된 디스패처에서 재개한다. |

`ATOMIC`은 시작 단계에 관한 옵션이다. 아래 예제에서 본문은 취소 요청 뒤에도 시작되지만 `yield()`에서 취소를 감지한다. 독립 실습 모듈의 `main`에서 예제를 실행하려면 `implementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.10.2")`를 추가한다. `runTest`와 `runCurrent()`로 예약된 작업이 실행되는 시점을 제어한다. [kotlinx.coroutines · `CoroutineStart`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-start/) · [kotlinx.coroutines · `ATOMIC`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-start/-a-t-o-m-i-c/) · [kotlinx.coroutines · `runTest`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-test/kotlinx.coroutines.test/run-test.html)

```kotlin
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.DelicateCoroutinesApi
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.yield

@OptIn(DelicateCoroutinesApi::class, ExperimentalCoroutinesApi::class)
fun main() = runTest {
    val events = mutableListOf<String>()
    val normal = launch(start = CoroutineStart.DEFAULT) { events.add("default") }
    val atomic = launch(start = CoroutineStart.ATOMIC) {
        events.add("atomic entered")
        yield()
        events.add("atomic resumed")
    }
    normal.cancel()
    atomic.cancel()
    runCurrent()
    check(events == listOf("atomic entered"))

    val lazy = launch(start = CoroutineStart.LAZY) { events.add("lazy entered") }
    check(!lazy.isActive && !lazy.isCompleted)
    lazy.start()
    runCurrent()

    launch(start = CoroutineStart.UNDISPATCHED) {
        events.add("undispatched entered")
        yield()
        events.add("undispatched resumed")
    }
    check(events == listOf("atomic entered", "lazy entered", "undispatched entered"))
    runCurrent()
    check(events.last() == "undispatched resumed")
}
```

## 4. `Dispatchers.Unconfined`의 재개 위치

`Dispatchers.Unconfined`는 호출 스레드에서 실행을 시작한다. 실제로 중단된 뒤에는 해당 중단 함수의 재개 방식에 따라 스레드가 정해진다. 아래에서는 `CompletableDeferred`를 전용 작업 스레드에서 완료하므로, 그 스레드에서 코루틴이 재개되는 것을 확인할 수 있다. UI 스레드나 특정 실행기에서 재개해야 하는 코드는 그 위치를 보장하는 디스패처를 사용한다. [kotlinx.coroutines · `Dispatchers.Unconfined`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-unconfined.html)

```kotlin
import java.util.concurrent.Executors
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext

fun main() {
    val executor = Executors.newSingleThreadExecutor { task -> Thread(task, "callback-worker") }
    executor.asCoroutineDispatcher().use { worker ->
        runBlocking {
            val caller = Thread.currentThread()
            val ready = CompletableDeferred<Unit>()
            val threads = async(Dispatchers.Unconfined) {
                val before = Thread.currentThread()
                ready.await()
                before to Thread.currentThread()
            }

            withContext(worker) { ready.complete(Unit) }
            val (before, after) = threads.await()
            check(before === caller && after.name == "callback-worker")
        }
    }
}
```

## 5. `Continuation`으로 중단과 재개 관찰하기

`suspendCoroutine`에서 받은 `Continuation<T>`에는 중단 지점 이후에 필요한 재개 동작과 컨텍스트가 연결된다. `resume(value)`로 결과를 전달하거나 `resumeWith(Result.failure(error))`로 예외를 전달할 수 있다. 아래에서는 `startCoroutine`의 완료 콜백이 처음에는 호출되지 않는다. 중단된 지점의 `Continuation`에 값을 주면 그 지점부터 실행이 이어지고, 중단 전의 지역 변수 `prefix`를 사용해 결과를 만든다. [Kotlin 언어 명세 · 코루틴의 상태 머신](https://kotlinlang.org/spec/asynchronous-programming-with-coroutines.html) · [Kotlin · `suspendCoroutine`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.coroutines/suspend-coroutine.html) · [Kotlin · `Continuation`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.coroutines/-continuation/)

```kotlin
import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.resume
import kotlin.coroutines.startCoroutine
import kotlin.coroutines.suspendCoroutine

fun main() {
    var pending: Continuation<Int>? = null
    var outcome: Result<String>? = null
    val task: suspend () -> String = {
        val prefix = "stock:"
        val count = suspendCoroutine<Int> { pending = it }
        "$prefix $count"
    }

    task.startCoroutine(object : Continuation<String> {
        override val context = EmptyCoroutineContext

        override fun resumeWith(result: Result<String>) {
            outcome = result
        }
    })

    check(outcome == null)
    checkNotNull(pending).resume(3)
    check(checkNotNull(outcome).getOrThrow() == "stock: 3")
}
```

같은 중단 지점에 결과는 한 번만 전달한다. 콜백 API를 감싸면서 코루틴 취소와 콜백 등록 해제도 다뤄야 한다면 [02번의 `suspendCancellableCoroutine` 예제](02_kotlin_coroutine_scopes_context_and_continuations.md)를 참고한다.
