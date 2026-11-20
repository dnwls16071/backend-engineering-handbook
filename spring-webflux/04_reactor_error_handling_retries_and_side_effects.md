# Reactor Error Handling, Retries, and Side Effects

## 1. 실패를 처리할 범위 정하기

오류 신호는 현재 흐름을 종료한다. `onErrorResume`은 오류에 따라 대체 발행자로 전환하고, `onErrorReturn`은 대체 값 하나를 반환할 때 쓴다. `onErrorMap`은 오류를 업무 문맥에 맞는 타입으로 바꾼다. 항목별 조회 실패만 처리하려면 `flatMap`의 내부 조회에 오류 처리를 둔다. 오류 없이 값이 없는 상황은 `switchIfEmpty`로 처리한다. [Reactor · Handling Errors](https://projectreactor.io/docs/core/release/reference/coreFeatures/error-handling.html)

## 2. 일시적 오류에만 재시도 적용하기

`retryWhen`은 오류 뒤 상류를 다시 구독한다. 따라서 재구독할 때 작업이 실제로 다시 시작되는지 확인한다. 아래는 읽기 작업의 시도당 제한 시간, 일시적 오류의 백오프, 전체 제한 시간을 조합한 예다. 쓰기를 재시도할 때는 중복 실행이 발생해도 결과가 한 번의 처리와 같도록 설계해야 한다. [Reactor · Retrying](https://projectreactor.io/docs/core/release/reference/coreFeatures/error-handling.html) · [Reactor · Retry with Exponential Backoff](https://projectreactor.io/docs/core/release/reference/faq.html)

```java
import java.io.IOException;
import java.time.Duration;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;

import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

public class CatalogRetry {

    public static <T> Mono<T> fetch(Supplier<Mono<T>> lookup) {
        return Mono.defer(lookup)
                .timeout(Duration.ofMillis(500))
                .retryWhen(Retry.backoff(2, Duration.ofMillis(100))
                        .maxBackoff(Duration.ofMillis(300))
                        .filter(error -> error instanceof IOException || error instanceof TimeoutException)
                        .onRetryExhaustedThrow((spec, signal) -> signal.failure()))
                .timeout(Duration.ofSeconds(3));
    }
}
```

이 예제는 최초 호출 뒤 최대 두 번 더 시도한다. 실제 HTTP 클라이언트가 오류를 감싸서 전달한다면 재시도 분류를 그 타입에 맞춘다. 재시도를 적용하기 전·후 중 어디에 오류 관찰을 두느냐에 따라 개별 시도 실패와 최종 실패를 서로 다른 지표로 볼 수 있다.

## 3. 신호를 관찰하는 부수 효과

| 연산자 | 관찰하는 시점 |
| --- | --- |
| `doOnNext` | 값이 전달될 때 |
| `doOnError` | 에러 신호가 전달될 때 |
| `doOnCancel` | 취소될 때 |
| `doFinally` | 완료, 오류 또는 취소로 종료될 때 |

`doOn...` 계열은 로깅과 지표처럼 신호를 관찰하는 데 사용한다. 값의 변경은 `map`, 결과를 기다려야 하는 비동기 작업은 `flatMap`이나 `then`으로 흐름에 포함한다. 관찰 콜백도 실행 스레드를 사용하므로 로그 전송처럼 오래 걸리는 블로킹 작업을 그 자리에서 기다리면 지연이 전파될 수 있다. [Reactor · Peeking into a Sequence](https://projectreactor.io/docs/core/release/reference/apdx-operatorChoice.html) · [Reactor · doFinally](https://projectreactor.io/docs/core/release/reference/coreFeatures/error-handling.html)
