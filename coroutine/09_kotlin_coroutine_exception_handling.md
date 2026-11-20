# Kotlin Coroutine Exception Handling: Propagation, Supervision, and Cancellation

코루틴에서 예외를 처리할 위치는 실패를 어디까지 전달해야 하는지에 따라 달라진다. 함께 성공해야 하는 작업은 실패를 공유하고, 일부 결과만 있어도 되는 작업은 자식의 실패를 격리한다. 예제는 Java 17과 [01번의 `kotlinx-coroutines-core` 1.10.2 설정](01_kotlin_coroutine_fundamentals_jobs_and_cancellation.md)을 사용한다.

## 1. 자식의 예외가 부모에게 전파되는 과정

일반 `coroutineScope`의 자식에서 `CancellationException` 외의 예외가 빠져나오면 부모 스코프가 실패한다. 같은 부모 아래 실행 중인 다른 자식도 취소되고, 그 작업들의 정리가 끝난 뒤 `coroutineScope` 호출이 예외를 던진다. 반환값이 없는 `launch`와 결과를 갖는 `async` 모두 이 부모·자식 규칙을 따른다. [Kotlin · 코루틴 예외 전파](https://kotlinlang.org/docs/exception-handling.html) · [kotlinx.coroutines · `coroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html)

예를 들어 주문 가능 수량을 계산하는 데 재고와 예약 수량이 모두 필요하다면, 한 조회만 성공해도 결과를 만들 수 없다. 두 조회를 같은 일반 스코프에 두면 하나가 실패했을 때 아직 진행 중인 조회를 취소할 수 있다.

## 2. `supervisorScope`와 `SupervisorJob`으로 전파 범위 제한하기

| 사용 위치 | 선택 기준 |
| --- | --- |
| `supervisorScope { ... }` | 한 호출 안에서 여러 자식 작업을 실행하고, 일부 실패를 개별적으로 처리한다. 블록과 자식의 종료를 기다린다. |
| `CoroutineScope(SupervisorJob(parent) + dispatcher)` | 호출 범위보다 오래 살아 있는 컴포넌트에서 자식의 실패를 개별적으로 처리한다. 소유자가 종료될 때 스코프를 취소한다. |

감독 스코프의 직접 자식이 실패해도 감독 스코프와 다른 직접 자식은 자동으로 취소되지 않는다. 감독 스코프 자체가 취소되거나 `supervisorScope` 블록 밖으로 예외가 나가면 그 자식들도 취소된다. `SupervisorJob(parent)`에 부모가 있으면 부모의 취소도 아래로 전파된다. 각 자식은 자신의 예외를 처리하거나 보고할 방법이 필요하다. [kotlinx.coroutines · `supervisorScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/supervisor-scope.html) · [kotlinx.coroutines · `SupervisorJob`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-supervisor-job.html)

## 3. `CoroutineExceptionHandler`로 미처리 예외 보고하기

`CoroutineExceptionHandler`는 다른 전파 경로가 없는 미처리 예외를 보고하는 마지막 수단이다. 일반 자식 `launch`의 실패는 먼저 부모 쪽으로 전달되므로, 그 자식에만 핸들러를 추가해도 실패 전파를 차단할 수 없다. 감독 스코프의 `launch` 자식에서 처리하지 않은 예외는 핸들러로 보고할 수 있다. 실패한 코루틴에서 대체 결과를 만들거나 재시도하는 일은 해당 작업 안의 `try/catch`로 처리한다. [kotlinx.coroutines · `CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineName
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.supervisorScope
import kotlinx.coroutines.withTimeout

fun main() = runBlocking {
    val reported = CompletableDeferred<Pair<String?, String?>>()
    val handler = CoroutineExceptionHandler { context, error ->
        reported.complete(context[CoroutineName]?.name to error.message)
    }

    supervisorScope {
        val store = launch(CoroutineName("store") + handler) { error("store unavailable") }
        val warehouse = async { 7 }

        check(withTimeout(5_000) { reported.await() } == ("store" to "store unavailable"))
        store.join()
        check(store.isCancelled && warehouse.await() == 7)
    }
}
```

## 4. `try/catch`를 어디에 둘지 결정하기

자식 작업이 예상 가능한 실패를 복구할 수 있으면 그 작업의 본문에 `try/catch`를 둔다. 여러 자식이 묶인 호출 전체가 실패했을 때만 대체 응답을 보내려면 `coroutineScope` 호출을 감싼다. `launch { ... }` 호출만 감싼 `try/catch`는 빌더 호출 시점의 예외를 처리한다. 시작된 코루틴 본문의 실패는 자기 본문의 `try/catch`나 스코프를 통해 처리한다. [Kotlin · 코루틴 예외 처리](https://kotlinlang.org/docs/exception-handling.html) · [kotlinx.coroutines · `coroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html)

```kotlin
import java.io.IOException
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

suspend fun readStock(): Int = throw IOException("stock source unavailable")

fun main() = runBlocking {
    var display: String? = null
    val task = launch {
        display = try {
            "${readStock()} units"
        } catch (_: IOException) {
            "unknown"
        }
    }
    task.join()
    check(display == "unknown" && !task.isCancelled)

    val response = try {
        coroutineScope {
            launch { readStock() }
            "ready"
        }
    } catch (_: IOException) {
        "unavailable"
    }
    check(response == "unavailable")
}
```

## 5. `async`의 실패를 `await()`에서 처리하기

`async`의 예외는 `Deferred`에 결과로 기록되며 `await()`가 그 예외를 던진다. 일반 스코프에서는 그 실패가 `await()` 호출 전에도 부모에 전파될 수 있다. 선택적 조회처럼 실패를 개별 값으로 처리하려면 `supervisorScope`에서 시작하고, `await()`에서 예상한 실패 타입을 잡는다. [kotlinx.coroutines · `async`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/async.html) · [kotlinx.coroutines · `Deferred.await`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-deferred/await.html)

```kotlin
import java.io.IOException
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.supervisorScope

fun main() = runBlocking {
    val failedScope = try {
        coroutineScope {
            async<Int> { throw IOException("required lookup failed") }
            "ready"
        }
    } catch (_: IOException) {
        "unavailable"
    }
    check(failedScope == "unavailable")

    val total = supervisorScope {
        val primary = async { 7 }
        val optional = async<Int> { throw IOException("optional lookup failed") }
        val optionalStock = try {
            optional.await()
        } catch (_: IOException) {
            0
        }
        primary.await() + optionalStock
    }
    check(total == 7)
}
```

## 6. 부모를 실패시키지 않는 취소 예외

`CancellationException`은 코루틴의 취소를 나타낸다. 자식 하나가 이 예외로 끝나면, 부모와 형제는 그 이유만으로 실패하거나 취소되지 않는다. `CoroutineExceptionHandler`도 이런 취소를 미처리 실패로 보고하지 않는다. 반대로 부모가 취소되면 자식에게 취소가 전달된다. `Exception`처럼 넓은 타입으로 예외를 잡아야 할 때는 잡은 `CancellationException`을 다시 던진다. [Kotlin · 취소와 예외](https://kotlinlang.org/docs/exception-handling.html)

`withTimeout()`의 `TimeoutCancellationException`도 `CancellationException`이다. 제한 시간을 넘겼을 때 값이 없음을 표시하는 작업에는 `withTimeoutOrNull()`로 `null`을 반환할 수 있다. [kotlinx.coroutines · `withTimeout`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-timeout.html) · [kotlinx.coroutines · `withTimeoutOrNull`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-timeout-or-null.html)

```kotlin
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull

fun main() = runBlocking {
    val skipped = launch { throw CancellationException("skip optional lookup") }
    val warehouse = async { 7 }

    skipped.join()
    check(skipped.isCancelled && warehouse.await() == 7)

    val timedOut = withTimeoutOrNull<Int>(10) { awaitCancellation() }
    check(timedOut == null && isActive)
}
```
