# Kotlin Coroutine Fundamentals: Jobs, Cancellation, and Exceptions

코루틴은 결과를 기다리는 동안 실행을 중단하고, 준비가 되면 중단한 지점에서 이어서 실행한다. 여러 작업을 시작하기 전에 어느 스코프가 작업의 완료를 기다리고, 취소와 실패를 어떻게 전달할지 정한다.

예제는 Java 17과 `kotlinx-coroutines-core` 1.10.2를 사용한다. `build.gradle.kts`에 아래 의존성을 추가하고, `main`이 있는 예제는 각각 별도 Kotlin 파일에서 실행한다. [Kotlin · 코루틴 기초와 의존성 설정](https://kotlinlang.org/docs/coroutines-basics.html)

```kotlin
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.10.2")
}
```

## 1. 루틴과 코루틴

일반 함수 호출은 호출한 스레드에서 함수 본문을 실행한 뒤 호출부로 돌아온다. `suspend` 함수는 `delay()`나 `Deferred.await()` 같은 중단 함수에서 실행을 잠시 멈출 수 있다. 중단 동안 스레드는 다른 코루틴을 실행할 수 있고, 결과가 준비되면 중단 지점 이후부터 이어서 실행한다. `suspend`는 함수에 중단을 허용한다. 새 코루틴이 필요한 경우에는 `launch`나 `async` 같은 빌더를 호출한다. [Kotlin · 중단 함수와 구조화된 동시성](https://kotlinlang.org/docs/coroutines-basics.html)

아래에서 `started`는 자식이 작업을 시작했다는 신호다. 자식은 `canFinish`를 기다리고, 부모는 그동안 다른 작업을 한 뒤 신호를 보내 결과를 받는다.

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking

suspend fun loadStock(canFinish: Deferred<Unit>): Int {
    canFinish.await()
    return 3
}

fun main() = runBlocking {
    val events = mutableListOf<String>()
    val started = CompletableDeferred<Unit>()
    val canFinish = CompletableDeferred<Unit>()
    val request = async {
        events.add("load requested")
        started.complete(Unit)
        val stock = loadStock(canFinish)
        events.add("load finished")
        stock
    }

    started.await()
    events.add("other work")
    canFinish.complete(Unit)

    check(request.await() == 3)
    check(events == listOf("load requested", "other work", "load finished"))
}
```

## 2. 스레드와 코루틴

스레드는 JVM에서 코드를 실행하는 단위다. 코루틴은 중단되기 전까지 스레드에서 실행되며, 디스패처에 따라 같은 스레드나 다른 스레드에서 재개될 수 있다. 단일 스레드에서도 중단 지점을 기준으로 여러 작업을 번갈아 진행할 수 있다. 여러 스레드에서 동시에 실행될 때는 병렬 실행도 가능하다. [Kotlin · 코루틴 컨텍스트와 디스패처](https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html)

| 디스패처 또는 호출 | 쓰는 기준 |
| --- | --- |
| `Dispatchers.Default` | CPU를 사용하는 계산 작업에 쓴다. |
| `Dispatchers.IO` | 파일 읽기 같은 블로킹 I/O를 실행하는 데 쓴다. |
| `withContext(dispatcher) { ... }` | 블록에 지정한 컨텍스트를 적용하고 결과를 호출부에 돌려준다. |

함수에 `suspend`를 붙여도 블로킹 API의 실행 방식은 그대로다. 예제에서는 `Files.readString`을 `Dispatchers.IO`에서 호출한다. `Default`와 `IO`는 JVM에서 스레드를 공유할 수 있으므로 디스패처를 바꿀 때마다 스레드가 바뀐다고 가정하지 않는다. [kotlinx.coroutines · `Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)

```kotlin
import java.nio.file.Files
import java.nio.file.Path
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext

suspend fun readStock(path: Path): Int = withContext(Dispatchers.IO) {
    Files.readString(path).trim().toInt()
}

fun main() = runBlocking {
    val file = Files.createTempFile("stock-", ".txt")
    try {
        Files.writeString(file, "3\n")
        check(readStock(file) == 3)
    } finally {
        Files.deleteIfExists(file)
    }
}
```

## 3. 코루틴 빌더와 `Job`

| 호출 | 반환값과 역할 |
| --- | --- |
| `runBlocking { ... }` | 블록과 자식 작업이 끝날 때까지 호출 스레드를 막고 블록 결과를 반환한다. `main`처럼 일반 함수에서 코루틴 코드로 진입할 때 사용할 수 있다. |
| `launch { ... }` | 결과값 없이 작업을 실행하고 생명주기를 다루는 `Job`을 반환한다. `join()`으로 완료를 기다린다. |
| `async { ... }` | 결과를 반환할 작업을 실행하고 `Deferred<T>`를 반환한다. `await()`로 결과를 받거나 해당 작업의 실패를 전달받는다. |
| `coroutineScope { ... }` | 중단 함수 안에서 작업 범위를 만들고, 블록과 자식 작업이 모두 끝나면 블록 결과를 반환한다. |

`join()`은 작업의 완료를 기다린다. 작업에서 계산한 값이나 실패를 받아야 하면 `Deferred.await()`를 사용한다. `CoroutineStart.LAZY`로 만든 작업은 처음에는 `New` 상태이며, `start()`나 `join()`으로 시작할 수 있다. 지연 시작한 `Deferred`는 `await()`로도 시작한다. [kotlinx.coroutines · `launch`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/launch.html) · [kotlinx.coroutines · `async`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/async.html) · [kotlinx.coroutines · `runBlocking`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html)

```kotlin
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

suspend fun availableStock(): Int = coroutineScope {
    val inStore = async { 4 }
    val inWarehouse = async { 7 }
    inStore.await() + inWarehouse.await()
}

fun main() = runBlocking {
    var saved = false
    val save = launch(start = CoroutineStart.LAZY) { saved = true }
    check(!save.isActive && !save.isCompleted && !save.isCancelled)
    check(!saved && save.start())
    save.join()

    check(saved && save.isCompleted && !save.isCancelled)
    check(availableStock() == 11)
}
```

## 4. 코루틴의 협력적 취소

`cancel()`은 취소를 요청한다. 코루틴은 `delay()`나 `awaitCancellation()`처럼 취소를 지원하는 중단 함수에서 취소를 감지한다. 중단 지점이 없는 계산 루프는 `currentCoroutineContext().ensureActive()`를 적절한 간격으로 호출해 취소를 확인할 수 있다. `cancelAndJoin()`은 취소를 요청하고 `finally` 같은 정리 작업까지 끝나기를 기다린다. [kotlinx.coroutines · `ensureActive`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/ensure-active.html) · [kotlinx.coroutines · `cancelAndJoin`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/cancel-and-join.html)

취소는 보통 `CancellationException`으로 전달된다. `catch (e: Exception)`처럼 넓게 잡는 코드에서 취소 예외를 받았다면 다시 던져 취소가 이어지게 한다. `finally`에서 파일 닫기 같은 정리를 수행한다. [Kotlin · 코루틴 예외와 취소](https://kotlinlang.org/docs/exception-handling.html)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

fun main() = runBlocking {
    val started = CompletableDeferred<Unit>()
    var released = false
    val job = launch {
        try {
            started.complete(Unit)
            awaitCancellation()
        } finally {
            released = true
        }
    }

    started.await()
    job.cancelAndJoin()

    check(released)
    check(job.isCancelled && job.isCompleted && !job.isActive)
}
```

## 5. 예외 전파와 `Job`의 상태 변화

| 상태 | `isActive` | `isCompleted` | `isCancelled` |
| --- | --- | --- | --- |
| `New` | `false` | `false` | `false` |
| `Active` | `true` | `false` | `false` |
| `Completing` | `true` | `false` | `false` |
| `Cancelling` | `false` | `false` | `true` |
| `Completed` | `false` | `true` | `false` |
| `Cancelled` | `false` | `true` | `true` |

`Completing`은 본문이 끝나고 자식 작업의 종료를 기다리는 중간 상태다. 취소나 실패를 처리하는 중에는 `Cancelling`이고, 자식과 정리 작업이 끝나면 `Cancelled`가 된다. 따라서 `isCancelled`가 먼저 `true`가 될 수 있다. [kotlinx.coroutines · `Job` 상태 표](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-job/)

- `coroutineScope`에서 자식이 `CancellationException` 외의 예외로 실패하면 같은 스코프의 다른 자식도 취소되고, 스코프 호출이 실패를 던진다. 일반 스코프에서 `async`를 써도 자식의 실패는 부모에 전파된다. [Kotlin · 코루틴 예외 전파](https://kotlinlang.org/docs/exception-handling.html)
- `supervisorScope`에서는 한 자식의 실패가 다른 자식을 자동으로 취소하지 않는다. 실패한 `async` 작업의 예외는 `await()`에서 처리할 수 있다. 처리하지 않은 예외가 스코프 블록 밖으로 전파되면 해당 스코프의 자식도 취소된다. [kotlinx.coroutines · `supervisorScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/supervisor-scope.html)
- `CoroutineExceptionHandler`는 다른 전파 경로가 없는 미처리 예외를 보고할 때 쓰인다. 예외가 난 작업의 복구나 재시도는 작업 안의 `try`·`catch` 또는 스코프를 호출하는 코드에서 다룬다. [kotlinx.coroutines · `CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.supervisorScope

fun main() = runBlocking {
    var siblingReleased = false
    val failure = try {
        coroutineScope {
            val siblingStarted = CompletableDeferred<Unit>()
            launch {
                try {
                    siblingStarted.complete(Unit)
                    awaitCancellation()
                } finally {
                    siblingReleased = true
                }
            }
            launch {
                siblingStarted.await()
                error("stock read failed")
            }
        }
        null
    } catch (e: IllegalStateException) {
        e
    }
    check(failure?.message == "stock read failed" && siblingReleased)

    supervisorScope {
        val failed = async<Int> { error("store read failed") }
        val warehouse = async { 7 }

        val error = try {
            failed.await()
            null
        } catch (e: IllegalStateException) {
            e
        }

        check(error?.message == "store read failed")
        check(failed.isCancelled && failed.isCompleted)
        check(warehouse.await() == 7)
    }
}
```
