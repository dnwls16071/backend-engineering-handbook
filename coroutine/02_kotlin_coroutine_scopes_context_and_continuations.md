# Kotlin Coroutine Structure: Scopes, Context, and Continuations

스코프는 작업의 수명을 묶고, 컨텍스트는 코루틴이 어떤 `Job`과 디스패처를 사용할지 정한다. `suspend` 함수가 중단되면 `Continuation`을 통해 실행을 이어 갈 수 있다. 예제는 01번 문서와 같은 Java 17과 `kotlinx-coroutines-core` 1.10.2를 사용하며, 각 코드는 별도 Kotlin 파일에서 실행할 수 있다. [실습 의존성 설정](01_kotlin_coroutine_fundamentals_jobs_and_cancellation.md)

## 1. 구조화된 동시성

`coroutineScope`에서 `launch`나 `async`로 만든 작업은 스코프의 자식이다. 스코프 본문이 끝나도 자식이 남아 있으면 호출부로 돌아가지 않는다. 부모가 취소되면 자식에게 취소가 전파되고, 일반 스코프의 자식이 `CancellationException` 외의 예외로 실패하면 스코프와 다른 자식도 취소된다. 독립적으로 실패해도 되는 작업을 모을 때는 `supervisorScope`를 고려한다. [kotlinx.coroutines · `coroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html) · [kotlinx.coroutines · `supervisorScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/supervisor-scope.html)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

suspend fun generateReport(events: MutableList<String>): Unit = coroutineScope {
    val bodyReady = CompletableDeferred<Unit>()
    launch {
        bodyReady.await()
        events.add("child completed")
    }
    events.add("body completed")
    bodyReady.complete(Unit)
}

fun main() = runBlocking {
    val events = mutableListOf<String>()
    generateReport(events)
    events.add("caller resumed")

    check(events == listOf("body completed", "child completed", "caller resumed"))
}
```

## 2. `CoroutineScope`와 `CoroutineContext`

| 구성 | 역할 |
| --- | --- |
| `CoroutineScope` | `coroutineContext`를 제공하고 `launch`, `async`가 자식 작업을 만들 기준이 된다. |
| `CoroutineContext` | 키가 있는 요소들을 묶는다. `Job`은 수명, 디스패처는 실행 위치, `CoroutineName`은 디버깅에 쓰는 이름을 제공한다. |
| `currentCoroutineContext()` | 중단 함수가 현재 실행 중인 코루틴의 컨텍스트를 읽는다. |

빌더는 스코프의 컨텍스트를 상속하고, 추가로 전달한 요소는 같은 키의 기존 요소를 바꾼다. 예를 들어 `async(CoroutineName("stock"))`은 이름을 바꾸면서 자식 `Job`을 만든다. 빌더에 별도 `Job`을 전달하면 기존 부모와의 관계가 달라질 수 있다. 요청 단위의 일에는 `coroutineScope`가 맞고, 장기간 살아 있는 컴포넌트가 스코프를 직접 만들면 컴포넌트 종료 시 그 스코프를 취소한다. [Kotlin · 컨텍스트 상속과 디스패처](https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html) · [kotlinx.coroutines · `CoroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-scope/)

```kotlin
import kotlinx.coroutines.CoroutineName
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.runBlocking

fun main() = runBlocking(CoroutineName("report")) {
    val parentJob = checkNotNull(coroutineContext[Job])
    val inheritedName = async { currentCoroutineContext()[CoroutineName]?.name }.await()
    val childContext = async(CoroutineName("stock")) {
        val context = currentCoroutineContext()
        check(parentJob.children.any { it === context[Job] })
        context
    }.await()

    check(inheritedName == "report")
    check(childContext[CoroutineName]?.name == "stock")
    check(childContext[Job] !== parentJob)
}
```

## 3. `suspend` 함수와 호출 흐름

`suspend` 함수는 다른 중단 함수를 호출할 수 있다. 런타임에 결과가 이미 준비되어 있으면 중단 없이 완료될 수도 있다. `val stock = loadStock()` 다음 줄은 중단 여부와 관계없이 호출 결과가 준비된 뒤 실행된다. 여러 `suspend` 호출을 차례로 적으면 순차 실행된다. 독립된 호출을 겹쳐 실행하려면 스코프 안에서 `async` 같은 빌더로 자식을 시작한다. [Kotlin · 중단 함수 합성](https://kotlinlang.org/docs/composing-suspending-functions.html)

```kotlin
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking

suspend fun loadQuantity(sku: String): Int? {
    delay(1)
    return if (sku == "pen") 3 else null
}

suspend fun stockLabel(sku: String): String {
    val quantity = loadQuantity(sku) ?: return "Out of stock"
    return "$sku: $quantity"
}

fun main() = runBlocking {
    check(stockLabel("pen") == "pen: 3")
    check(stockLabel("eraser") == "Out of stock")
}
```

## 4. 코루틴과 `Continuation`

`Continuation<T>`는 중단 이후 이어서 실행할 지점과 코루틴 컨텍스트를 표현한다. `resumeWith(Result.success(value))`로 값을, `resumeWith(Result.failure(error))`로 예외를 전달할 수 있다. Kotlin 컴파일러는 중단 지점이 있는 함수를 상태 머신으로 변환할 수 있다. 실제로 중단되면 재개 위치와 이후에 필요한 지역 값을 보존한다. [Kotlin 언어 명세 · 코루틴의 상태 머신](https://kotlinlang.org/spec/asynchronous-programming-with-coroutines.html) · [Kotlin · `Continuation`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.coroutines/-continuation/)

한 번 결과를 전달하는 콜백 API는 `suspendCancellableCoroutine`으로 감쌀 수 있다. 아래 예제는 등록한 콜백을 한 번만 꺼내 실행한다. 취소되면 `invokeOnCancellation`에서 콜백을 해제한다. 실제 콜백 API에서도 취소와 결과 전달이 겹칠 수 있으므로 등록과 해제는 스레드 안전해야 한다. [kotlinx.coroutines · `suspendCancellableCoroutine`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/suspend-cancellable-coroutine.html)

```kotlin
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.suspendCancellableCoroutine

class StockRequest {
    private val pending = AtomicReference<((Result<Int>) -> Unit)?>(null)

    fun register(callback: (Result<Int>) -> Unit) {
        check(pending.compareAndSet(null, callback))
    }

    fun unregister(callback: (Result<Int>) -> Unit) {
        pending.compareAndSet(callback, null)
    }

    fun complete(result: Result<Int>): Boolean {
        val callback = pending.getAndSet(null) ?: return false
        callback(result)
        return true
    }
}

suspend fun awaitStock(request: StockRequest): Int =
    suspendCancellableCoroutine { continuation ->
        val callback: (Result<Int>) -> Unit = { result -> continuation.resumeWith(result) }
        request.register(callback)
        continuation.invokeOnCancellation { request.unregister(callback) }
    }

fun main() = runBlocking {
    val request = StockRequest()
    val stock = async(start = CoroutineStart.UNDISPATCHED) { awaitStock(request) }
    check(request.complete(Result.success(3)))
    check(stock.await() == 3)
    check(!request.complete(Result.success(4)))

    val pending = StockRequest()
    val job = launch(start = CoroutineStart.UNDISPATCHED) { awaitStock(pending) }
    job.cancelAndJoin()
    check(job.isCancelled && !pending.complete(Result.success(5)))
}
```

`UNDISPATCHED`는 이 예제에서 콜백 등록이 첫 중단 지점까지 진행된 뒤 `complete`나 `cancelAndJoin`을 호출하도록 시작 순서를 맞춘다. 재개 후 실행 위치는 코루틴 컨텍스트에 따른다. [kotlinx.coroutines · `CoroutineStart.UNDISPATCHED`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-start/-u-n-d-i-s-p-a-t-c-h-e-d/)

## 5. 적용 예시와 선택 기준

한 요청에서 재고와 예약 수량을 각각 조회한다면 `coroutineScope` 안에서 두 조회를 시작하고 `await`로 합칠 수 있다. 두 조회가 모두 필요하므로 하나가 실패하면 남은 조회도 취소되는 구조를 사용한다. 차례대로 처리해야 할 작업은 `suspend` 함수를 순서대로 호출한다. 외부 콜백 API를 사용해야 할 때는 어댑터에 등록과 취소 동작을 함께 둔다. [Kotlin · 중단 함수의 동시 합성](https://kotlinlang.org/docs/composing-suspending-functions.html)

```kotlin
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking

suspend fun availableStock(
    sku: String,
    loadInventory: suspend (String) -> Int,
    loadReservations: suspend (String) -> Int,
): Int = coroutineScope {
    val inventory = async { loadInventory(sku) }
    val reservations = async { loadReservations(sku) }
    (inventory.await() - reservations.await()).coerceAtLeast(0)
}

fun main() = runBlocking {
    check(availableStock("pen", { 7 }, { 3 }) == 4)
    check(availableStock("pen", { 2 }, { 3 }) == 0)
}
```
