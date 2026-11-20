# Kotlin Suspending Functions: Execution and Composition

`suspend` 함수는 결과를 기다릴 때 실행을 잠시 멈췄다가 이어 갈 수 있다. 호출부는 일반 함수처럼 반환값을 받으므로, 앞의 결과가 필요한 단계는 순서대로 쓰고 서로 독립된 단계만 자식 코루틴으로 시작할 수 있다. 예제는 Java 17과 [01번의 `kotlinx-coroutines-core` 1.10.2 설정](01_kotlin_coroutine_fundamentals_jobs_and_cancellation.md)을 사용한다.

## 1. 일시 중단 함수와 코루틴

`suspend fun`은 중단 함수를 직접 호출할 수 있는 함수다. 다른 중단 함수나 `launch`·`async`의 코루틴 블록에서 호출할 수 있다. 일반 함수에서 중단 코드로 진입하는 `main` 같은 경계에서는 `runBlocking`을 사용할 수 있다. [Kotlin · 코루틴 기초](https://kotlinlang.org/docs/coroutines-basics.html) · [Kotlin 언어 명세 · 일시 중단 함수](https://kotlinlang.org/spec/asynchronous-programming-with-coroutines.html)

직접 호출한 일시 중단 함수는 호출한 코루틴의 일부로 실행된다. `launch`나 `async`를 별도로 쓰면 자식 코루틴이 만들어진다. 결과가 이미 준비된 경로는 바로 값을 반환할 수 있고, 중단이 필요한 경로는 결과가 준비된 뒤 호출 흐름을 이어 간다. 아래 함수는 캐시가 있으면 곧바로 반환하고, 없으면 `suspend () -> Int` 타입의 조회 함수를 호출한다. [kotlinx.coroutines · `currentCoroutineContext`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/current-coroutine-context.html) · [kotlinx.coroutines · `delay`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/delay.html)

```kotlin
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking

suspend fun loadQuantity(cached: Int?, fetch: suspend () -> Int): Int = cached ?: fetch()

fun main() = runBlocking {
    val callerJob = checkNotNull(currentCoroutineContext()[Job])
    check(loadQuantity(4) { error("cache hit should skip fetching") } == 4)

    val quantity = loadQuantity(null) {
        delay(1)
        check(currentCoroutineContext()[Job] === callerJob)
        7
    }

    check(quantity == 7)
}
```

## 2. 일시 중단 함수 조합하기

### 앞선 결과가 필요한 작업과 독립된 작업

주문 번호로 SKU를 먼저 알아야 한다면 `findSku(orderId)`를 호출하고 그 결과를 다음 단계로 넘긴다. SKU가 준비되면 재고와 예약 수량을 독립적으로 조회할 수 있다. `coroutineScope`가 제공하는 `CoroutineScope` 안에서 두 `async`를 시작하고 결과를 합친다. 아래 예제에서는 각 조회가 다른 조회의 시작 신호를 기다리게 해, 두 작업이 결과를 받기 전에 모두 시작됐는지 확인한다. [Kotlin · 중단 함수의 순차·동시 합성](https://kotlinlang.org/docs/composing-suspending-functions.html) · [kotlinx.coroutines · `coroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout

suspend fun availableForOrder(
    orderId: String,
    findSku: suspend (String) -> String,
    loadStock: suspend (String) -> Int,
    loadReserved: suspend (String) -> Int,
): Int {
    val sku = findSku(orderId)
    return coroutineScope {
        val stock = async { loadStock(sku) }
        val reserved = async { loadReserved(sku) }
        (stock.await() - reserved.await()).coerceAtLeast(0)
    }
}

fun main() = runBlocking {
    val stockStarted = CompletableDeferred<Unit>()
    val reservedStarted = CompletableDeferred<Unit>()
    val available = withTimeout(5_000) {
        availableForOrder(
            orderId = "order-42",
            findSku = { id ->
                check(id == "order-42")
                "pen"
            },
            loadStock = { sku ->
                check(sku == "pen")
                stockStarted.complete(Unit)
                reservedStarted.await()
                7
            },
            loadReserved = { sku ->
                check(sku == "pen")
                reservedStarted.complete(Unit)
                stockStarted.await()
                3
            },
        )
    }
    check(available == 4)
}
```

### 블로킹 API에 실행 위치 지정하기

`suspend` 함수에서 블로킹 JDBC나 파일 API를 직접 호출하면 해당 호출이 끝날 때까지 현재 스레드를 점유한다. 블로킹 호출을 감싼 함수에서는 `withContext(Dispatchers.IO)`로 실행 위치를 지정할 수 있다. JVM에서 스레드 인터럽트에 반응하는 API라면 `runInterruptible(Dispatchers.IO)`로 코루틴 취소를 인터럽트에 연결할 수 있다. 아래 예제는 실행기를 주입해 실제 호출 위치와 결과 반환을 확인한다. [kotlinx.coroutines · `Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html) · [kotlinx.coroutines · `withContext`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-context.html) · [kotlinx.coroutines · `runInterruptible`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-interruptible.html)

```kotlin
import java.util.concurrent.Executors
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext

class StockRepository(
    private val blockingRead: (String) -> Int,
    private val io: CoroutineDispatcher = Dispatchers.IO,
) {
    suspend fun findQuantity(sku: String): Int = withContext(io) { blockingRead(sku) }
}

fun main() {
    val executor = Executors.newSingleThreadExecutor { task -> Thread(task, "stock-io-test") }
    executor.asCoroutineDispatcher().use { dispatcher ->
        runBlocking {
            val caller = Thread.currentThread()
            val repository = StockRepository(
                blockingRead = { sku ->
                    check(Thread.currentThread().name == "stock-io-test")
                    if (sku == "pen") 3 else 0
                },
                io = dispatcher,
            )

            check(repository.findQuantity("pen") == 3)
            check(Thread.currentThread() === caller)
        }
    }
}
```
