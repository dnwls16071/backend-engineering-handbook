# Structured Concurrency in Kotlin: Context Inheritance, Scopes, and Jobs

구조화된 동시성은 함께 끝나야 할 작업을 한 스코프에 묶는다. 부모는 자식까지 마쳐야 완료되고, 부모를 취소하면 묶인 작업도 함께 취소된다. 예제는 Java 17과 [01번의 `kotlinx-coroutines-core` 1.10.2 설정](01_kotlin_coroutine_fundamentals_jobs_and_cancellation.md)을 사용한다.

## 1. 실행 컨텍스트 상속하기

`launch`와 `async`는 스코프에서 디스패처나 이름 같은 컨텍스트 요소를 상속한다. 호출에 다른 이름이나 디스패처를 넘기면 같은 키의 요소를 바꿀 수 있다. 새 코루틴은 스코프의 `Job`에 연결된 별도 자식 `Job`을 가진다. [Kotlin · 자식 코루틴과 컨텍스트 상속](https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html) · [kotlinx.coroutines · `launch`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/launch.html)

JVM의 `ThreadLocal`에 있는 요청 ID를 작업 스레드에서도 사용해야 한다면 `asContextElement(value)`로 컨텍스트에 넣을 수 있다. 코루틴이 실행되는 동안 해당 스레드에 지정한 값을 설치하고, 실행이 중단되면 그 스레드의 이전 값을 복원한다. [kotlinx.coroutines · `ThreadLocal.asContextElement`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/as-context-element.html)

```kotlin
import kotlinx.coroutines.CoroutineName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.asContextElement
import kotlinx.coroutines.async
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.runBlocking

fun main() {
    val requestId = ThreadLocal<String>()
    runBlocking(CoroutineName("request") + requestId.asContextElement("req-42")) {
        val parent = checkNotNull(coroutineContext[Job])
        val result = async(Dispatchers.Default + CoroutineName("stock")) {
            val childContext = currentCoroutineContext()
            check(parent.children.any { it === childContext[Job] })
            childContext[CoroutineName]?.name to requestId.get()
        }.await()

        check(result == ("stock" to "req-42"))
        check(coroutineContext[CoroutineName]?.name == "request")
    }
    check(requestId.get() == null)
}
```

## 2. 부모와 자식의 작업 제어

| 상황 | 전파와 완료 규칙 |
| --- | --- |
| 부모의 본문이 정상 종료 | 자식이 모두 끝난 뒤 부모 `Job`이 완료된다. |
| 부모 취소 | 자식에게 취소가 전파된다. 부모의 완료는 자식의 정리까지 기다린다. |
| 자식이 `CancellationException`으로 취소 | 자식 하나의 취소로 부모나 형제가 자동 취소되지는 않는다. |
| 일반 스코프의 자식이 다른 예외로 실패 | 부모가 실패하고, 같은 부모 아래 남은 자식이 취소된다. |

[kotlinx.coroutines · `Job`의 부모·자식 관계](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-job/) · [Kotlin · 자식의 실패와 취소](https://kotlinlang.org/docs/exception-handling.html)

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

fun main() = runBlocking {
    val started = listOf("stock", "reservation").associateWith { CompletableDeferred<Unit>() }
    val cleaned = mutableSetOf<String>()
    val group = launch {
        for ((name, ready) in started) {
            launch {
                try {
                    ready.complete(Unit)
                    awaitCancellation()
                } finally {
                    cleaned.add(name)
                }
            }
        }
    }

    for (ready in started.values) ready.await()
    group.cancelAndJoin()

    check(cleaned == setOf("stock", "reservation"))
    check(group.isCancelled && group.isCompleted)
}
```

## 3. `CoroutineScope`를 컴포넌트의 수명과 연결하기

호출과 함께 끝나야 하는 작업에는 `coroutineScope`를 쓴다. 컴포넌트가 살아 있는 동안 계속 수행할 작업은 해당 컴포넌트가 소유하는 `CoroutineScope`에서 시작하고, 컴포넌트가 종료될 때 `scope.cancel()`을 호출한다. 서로 독립된 자식의 실패를 격리해야 하면 스코프에 `SupervisorJob`을 사용한다. `SupervisorJob` 자체를 취소하면 그 아래 자식도 취소된다. [kotlinx.coroutines · 사용자 정의 `CoroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-scope/) · [kotlinx.coroutines · `SupervisorJob`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-supervisor-job.html)

아래의 `close()`는 취소를 요청한다. 호출부에서 리소스 정리까지 기다려야 하면 작업의 `Job`에 `join()`을 호출한다.

```kotlin
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineName
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

class StockMonitor(dispatcher: CoroutineDispatcher = Dispatchers.Default) : AutoCloseable {
    private val scope = CoroutineScope(SupervisorJob() + dispatcher + CoroutineName("stock-monitor"))

    fun start(watch: suspend () -> Unit): Job = scope.launch { watch() }

    override fun close() {
        scope.cancel()
    }
}

fun main() = runBlocking {
    val monitor = StockMonitor()
    val watching = CompletableDeferred<Unit>()
    val released = CompletableDeferred<Unit>()
    val observer = monitor.start {
        try {
            watching.complete(Unit)
            awaitCancellation()
        } finally {
            released.complete(Unit)
        }
    }

    try {
        watching.await()
        check(observer.isActive)
    } finally {
        monitor.close()
    }
    observer.join()
    check(observer.isCancelled && released.isCompleted)
}
```

## 4. `Job(parent)`으로 만든 작업 그룹 관리하기

`Job(parent)`로 부모에 연결된 `CompletableJob`을 만들 수 있다. 직접 만든 그룹은 그 아래 코루틴이 모두 끝나도 자동으로 정상 완료되지 않는다. 그룹을 정상적으로 끝내려면 `complete()`를 호출하고, 실행 중인 일을 중단하려면 `cancel()`을 호출한다. 빌더 호출에 별도 `Job`을 넘겨 부모 관계를 바꾸기보다, 호출 범위에는 `coroutineScope`, 별도 수명에는 소유자가 있는 `CoroutineScope`를 사용한다. [kotlinx.coroutines · `Job(parent)`와 완료](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-job.html) · [kotlinx.coroutines · `CompletableJob`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-completable-job/)

```kotlin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

fun main() = runBlocking {
    val parent = Job()
    val group = Job(parent)
    val scope = CoroutineScope(group + Dispatchers.Default)

    try {
        check(parent.children.any { it === group })
        scope.launch { check(group.isActive) }.join()
        check(group.isActive && !group.isCompleted)

        check(group.complete())
        group.join()
        check(group.isCompleted && !group.isCancelled)
        parent.complete()
        parent.join()
    } finally {
        parent.cancel()
    }
}
```

## 5. `runBlocking`이 호출부로 돌아오는 시점

`runBlocking`은 일반 함수에서 중단 함수를 호출할 수 있게 연결한다. 호출 스레드가 반환을 기다리고, 기본 디스패처는 해당 스레드의 이벤트 루프에서 코루틴 실행을 처리한다. 블록이 값을 계산해도 자식이 끝날 때까지 반환하지 않는다. 이미 `suspend` 함수 안에서 자식 일을 묶을 때는 `coroutineScope`를 사용해 스레드를 차단하지 않고 기다린다. [kotlinx.coroutines · `runBlocking`과 이벤트 루프](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html) · [kotlinx.coroutines · `coroutineScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html)

```kotlin
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

fun main() {
    val caller = Thread.currentThread()
    var childFinished = false
    val report = runBlocking {
        launch {
            delay(1)
            check(Thread.currentThread() === caller)
            childFinished = true
        }
        "stock report"
    }

    check(report == "stock report" && childFinished)
}
```
