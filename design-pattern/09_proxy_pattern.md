# Proxy Pattern

프록시 패턴은 다른 객체에 대한 접근을 대리 객체를 통해 제어한다. 생성 비용이 큰 객체를 처음 사용할 때까지 미루거나, 특정 조건에서만 요청을 전달해야 할 때 적용할 수 있다.

## 구조와 선택 기준

클라이언트와 실제 객체는 공통 계약인 `Preview`를 공유한다. 가상 프록시는 이미지 미리보기의 첫 호출에서 실제 객체를 만들고, 이후 요청은 같은 객체에 전달한다. 접근 제어나 원격 호출을 다루는 프록시도 호출을 넘기는 시점과 방법을 맡는다.

같은 인터페이스를 제공하더라도 추가 지연이나 실패가 생길 수 있다. 예를 들어 생성 오류가 첫 접근 때 나타날 수 있으므로 호출자가 처리할 오류 계약을 확인한다. 캐싱을 도입한다면 데이터의 갱신 시점과 무효화 규칙도 함께 정한다. [데코레이터](16_decorator_pattern.md)는 같은 계약 위에 동작을 조합하며, 프록시는 대상을 언제 어떤 조건으로 접근하는지에 초점을 둔다.

## Java 17 예제

```java
import java.util.function.Supplier;

class ProxyExample {
    interface Preview {
        String show();
    }

    record ImagePreview(String fileName) implements Preview {
        @Override
        public String show() {
            return "Preview: " + fileName;
        }
    }

    static final class LazyPreview implements Preview {
        private final Supplier<Preview> loader;
        private Preview target;

        LazyPreview(Supplier<Preview> loader) {
            this.loader = loader;
        }

        @Override
        public String show() {
            if (target == null) {
                target = loader.get();
            }
            return target.show();
        }
    }

    public static void main(String[] args) {
        var loads = new java.util.concurrent.atomic.AtomicInteger();
        Preview preview = new LazyPreview(() -> {
            loads.incrementAndGet();
            return new ImagePreview("receipt.png");
        });

        if (loads.get() != 0
                || !preview.show().equals("Preview: receipt.png")
                || !preview.show().equals("Preview: receipt.png")
                || loads.get() != 1) {
            throw new AssertionError("Load on first access and reuse the preview");
        }
    }
}
```

미리보기를 두 번 요청해도 실제 객체는 첫 요청에서 한 번 생성된다. 예제는 한 스레드에서 실행한다. 여러 스레드가 같은 프록시를 쓴다면 최초 생성과 결과 공유의 동시성을 고려한다.

참고 [Design Patterns · Proxy](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610) · [Java 17 동적 프록시](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/reflect/Proxy.html)
