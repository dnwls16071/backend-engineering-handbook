# Reactor Operators for Stream Processing

## 1. 변환과 필터링

| 목적 | 연산자와 결과 |
| --- | --- |
| 값 하나를 다른 값으로 변환 | `map`은 입력마다 동기 함수 결과 하나를 전달한다. |
| 입력마다 비동기 조회 또는 여러 값 생성 | `flatMap`은 내부 발행자를 구독하고 도착한 값을 합친다. 완료 순서는 달라질 수 있다. |
| 비동기 처리를 입력 순서대로 진행 | `concatMap`은 내부 발행자를 순차 실행한다. 동시 실행과 입력 순서 유지를 함께 원하면 `flatMapSequential`의 동시성 및 버퍼 비용을 고려한다. |
| 조건을 만족하는 값만 전달 | `filter`로 조건을 검사한다. 빈 결과에는 완료 후 `switchIfEmpty`를 적용할 수 있다. |
| 앞부분을 잘라 사용 | `take(n)`은 지정한 개수까지만 전달하고 필요하면 상류를 취소한다. |

[Reactor · Operator Choice](https://projectreactor.io/docs/core/release/reference/apdx-operatorChoice.html)

## 2. 여러 스트림을 결합하기

`merge`는 여러 발행자의 값을 도착하는 순서대로 섞는다. `concat`은 현재 스트림이 완료된 뒤 다음 스트림을 구독한다. `zip`은 각 스트림에서 대응하는 값이 있어야 하나의 결과를 만든다. `Mono.zip`의 입력 하나가 값 없이 끝나면 조합 결과에도 값이 없다. 서로 독립적인 완료만 기다리면 `Mono.when(...)`을 사용할 수 있다. [Reactor · Combining Publishers](https://projectreactor.io/docs/core/release/reference/apdx-operatorChoice.html) · [Reactor · FAQ on zip](https://projectreactor.io/docs/core/release/reference/faq.html)

예를 들어 ID 순서를 유지하면서 비동기 조회를 진행하고 활성 상품만 전달할 수 있다.

```java
import java.util.function.Function;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

public class CatalogOperators {

    public record Product(String id, boolean active) {
    }

    public static Flux<String> activeIds(Flux<String> ids, Function<String, Mono<Product>> lookup) {
        return ids.concatMap(lookup)
                .filter(Product::active)
                .map(Product::id);
    }
}
```

## 3. 조건 검사와 집계에서 완료 시점 확인하기

- `any`는 일치하는 값을 찾으면 `true`로 종료할 수 있다. `false`는 입력이 끝날 때 결정된다.
- `all`은 반례가 나오면 `false`로 종료할 수 있다. `true`는 입력이 끝날 때 결정된다. 빈 스트림에서는 `true`다.
- `reduce`는 완료 시 집계 값을 내고 `scan`은 중간 집계 값을 전달한다.
- `collectList`는 완료까지 값을 보관한다. 입력이 오래 지속되거나 개수 제한이 없는 경우에는 업무상 의미 있는 시간·개수 단위로 `window`나 `buffer`를 적용한 뒤 그 구간을 집계한다.

[Reactor · Boolean Checks and Aggregation](https://projectreactor.io/docs/core/release/reference/apdx-operatorChoice.html)
