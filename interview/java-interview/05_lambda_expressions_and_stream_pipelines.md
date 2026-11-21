# Lambda Expressions and Stream Pipelines

## 1. 람다와 스트림이 무엇인가요?

**30–60초 답변**

> 람다 표현식은 메서드에 넘길 동작을 간결하게 표현합니다. 자바에서는 `Predicate<Order>`나 `Function<Order, Long>` 같은 함수형 인터페이스가 람다의 대상 타입이 됩니다. 스트림은 컬렉션이나 다른 소스의 요소를 `filter`, `map`, `reduce` 같은 연산으로 처리하는 API입니다. 예를 들어 `orders.stream().filter(order -> order.isPaid()).mapToLong(order -> order.total()).sum()`은 결제된 주문 금액을 합산합니다. 람다는 개별 연산의 동작을 정의하고 스트림은 그 연산을 파이프라인으로 연결합니다. [JLS §15.27 람다 표현식](https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html#jls-15.27) · [Java 8 스트림 API](https://docs.oracle.com/javase/8/docs/api/java/util/stream/package-summary.html)

**꼬리 질문 · 람다는 항상 새 객체를 만들고 지역 변수를 복사하나요?**

자바 명세는 람다를 평가할 때 구현이 기존 객체를 재사용할 수 있게 합니다. 람다가 바깥 지역 변수를 캡처하려면 그 변수가 `final`이거나 사실상 `final`이어야 합니다. 참조를 캡처한 경우 그 참조가 가리키는 객체까지 불변이 되는 것은 아닙니다. 예를 들어 다시 대입하지 않는 `List` 변수도, 리스트에 대한 `add()`는 가능할 수 있습니다. [JLS §15.27.2 람다 본문과 지역 변수](https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html#jls-15.27.2) · [JLS §15.27.4 람다의 런타임 평가](https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html#jls-15.27.4)

## 2. Java 8에서 람다와 스트림을 도입한 이유는 가독성뿐인가요?

**30–60초 답변**

> 람다는 동작을 인자로 전달하기 쉽게 해 API 호출자가 필터나 비교 기준을 표현할 수 있게 합니다. 스트림은 변환과 집계의 순서를 선언하고 요소를 실제로 순회하는 방식은 라이브러리에 맡기는 내부 반복을 제공합니다. 이 덕분에 여러 중간 연산을 순회 한 번에 처리하거나 결과가 충분할 때 탐색을 멈출 수 있습니다. 적합한 작업은 데이터 일부를 나눠 병렬로 집계할 수 있습니다. 실제 성능은 소스를 나누는 비용, 요소별 작업량, 연산 순서의 제약, 결과를 합치는 비용을 고려해 측정합니다. [JSR 335 람다 표현식 제안](https://www.jcp.org/en/jsr/detail?id=335) · [Java 8 스트림 API의 파이프라인과 병렬성](https://docs.oracle.com/javase/8/docs/api/java/util/stream/package-summary.html)

**꼬리 질문 · `parallelStream()`으로 바꿀 때 무엇을 먼저 확인하나요?**

공유 리스트나 카운터를 람다에서 직접 갱신하는지 봅니다. 병렬 `reduce()`를 사용한다면 결합 연산은 결합법칙을 만족해야 하고, 초기값은 항등원이어야 합니다. 예를 들어 `Integer::sum`에는 `0`을 초기값으로 사용할 수 있습니다. 실제 데이터 크기와 부하에서 순차·병렬 버전의 CPU 사용량과 처리 시간을 비교한 뒤 선택합니다. [Java 스트림의 감소 연산과 결합법칙](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/package-summary.html#Reduction)

## 3. 함수형 프로그래밍이란 무엇인가요?

**30–60초 답변**

> 함수형 프로그래밍은 계산을 값을 받아 값을 내는 함수의 조합으로 표현하는 방식입니다. 순수 함수는 같은 입력에 같은 결과를 내고 외부 상태를 바꾸지 않습니다. 예를 들어 주문 금액에 할인율을 적용해 새 금액을 반환하는 계산은 주문 객체나 DB를 수정하는 행위와 분리할 수 있습니다. Java에서는 람다와 함수형 인터페이스로 함수를 전달하고, 스트림으로 변환을 조합할 수 있습니다. Java에서 쓰기나 로깅도 람다에 넣을 수 있으므로 순수성은 개발자가 설계하는 성질입니다. [JLS §9.8 함수형 인터페이스](https://docs.oracle.com/javase/specs/jls/se25/html/jls-9.html#jls-9.8) · [Java 스트림 API의 상태 공유와 부수 효과](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/package-summary.html)

**꼬리 질문 · 외부 API 호출이나 DB 쓰기가 있으면 어떻게 설계하나요?**

할인 계산이나 입력 검증처럼 값으로 표현 가능한 부분은 입력과 결과를 명시하고 독립적으로 테스트합니다. 그 결과를 저장하거나 외부 서비스에 반영하는 일은 별도 단계에서 수행합니다. 파이프라인의 중간 연산에 꼭 수행해야 할 저장을 넣으면 단락 연산이나 최적화 때문에 호출이 생략될 수 있습니다. [Java `Stream`의 최적화와 부수 효과](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html)

## 4. 스트림의 지연 연산이 무엇인가요?

**30–60초 답변**

> `filter()`와 `map()` 같은 중간 연산을 호출하면 파이프라인 단계가 연결되고, 최종 연산이 실행되면 결과에 필요한 만큼 소스를 탐색합니다. 예를 들어 `Stream.of(1, 2, 3, 4).filter(n -> n % 2 == 0).findFirst()`는 순차 처리에서 첫 짝수 `2`를 찾으면 멈출 수 있습니다. 반면 `sorted()`가 중간에 있다면 임의 순서의 유한 입력에서는 첫 결과를 결정하기 전에 입력 전체를 보아야 할 수 있습니다. 최종 연산으로 소비된 스트림이 필요하면 소스에서 새 스트림을 만듭니다. [Java 8 스트림 API의 지연 연산과 단락 연산](https://docs.oracle.com/javase/8/docs/api/java/util/stream/package-summary.html)

**꼬리 질문 · `peek()` 뒤에 `count()`를 붙이면 모든 요소가 출력되나요?**

Java 9부터 API 문서는 소스의 요소 수를 직접 계산할 수 있으면 `count()`가 순회를 생략할 수 있다고 명시합니다. 소스의 크기가 알려져 있고 중간 연산이 요소 수를 바꾸지 않을 때가 한 예입니다. 예를 들어 `List.of(1, 2, 3).stream().peek(System.out::println).count()`는 `3`을 반환하면서 출력 단계를 생략할 수 있습니다. 반드시 필요한 출력은 `forEach()` 같은 계약이 명확한 최종 연산이나 별도 단계에서 수행합니다. [Java 9 `Stream.count()`의 API 설명](https://docs.oracle.com/javase/9/docs/api/java/util/stream/Stream.html#count--) · [Java 25 `Stream.count()`의 API 설명](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html#count())
