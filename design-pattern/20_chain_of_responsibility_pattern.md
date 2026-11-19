# Chain of Responsibility Pattern

어떤 처리기가 요청을 맡을지 호출 시점에 정해야 할 때, 처리기를 체인으로 연결할 수 있다. 요청을 받은 처리기는 자신의 조건에 해당하는지 판단하고, 해당하지 않으면 다음 처리로 넘긴다. 호출자는 체인의 첫 처리기로 요청을 보낸다.

## 처리 순서와 종료 조건 정하기

문의 분류에 적용하면 결제 담당과 배송 담당이 각자 맡을 유형을 검사한다. 첫 번째로 맡을 수 있는 처리기가 응답하고, 모두 통과하면 일치하는 담당자가 없다는 결과를 반환한다. 조건이 겹칠 수 있다면 연결 순서가 우선순위가 된다. [GoF의 Chain of Responsibility 패턴](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

```java
import java.util.Optional;

class ChainOfResponsibilityExample {
    enum Kind { BILLING, SHIPPING, OTHER }

    interface Handler {
        Optional<String> route(Kind kind);
    }

    record QueueHandler(Kind accepted, String queue, Handler next) implements Handler {
        @Override
        public Optional<String> route(Kind kind) {
            if (kind == accepted) {
                return Optional.of(queue);
            }
            return next.route(kind);
        }
    }

    public static void main(String[] args) {
        Handler noMatch = kind -> Optional.empty();
        Handler shipping = new QueueHandler(Kind.SHIPPING, "shipping", noMatch);
        Handler chain = new QueueHandler(Kind.BILLING, "billing", shipping);
        if (!chain.route(Kind.BILLING).equals(Optional.of("billing"))
                || !chain.route(Kind.SHIPPING).equals(Optional.of("shipping"))
                || chain.route(Kind.OTHER).isPresent()) {
            throw new AssertionError("Unexpected routing result");
        }
    }
}
```

결제 요청은 첫 처리기에서 끝난다. 배송 요청은 두 번째 처리기에서 처리되고, 기타 요청은 체인의 끝까지 간다. 종류별 직접 조회만 필요한 경우에는 맵이 간단할 수 있다. 처리기의 판정이 복잡하거나 순서에 따라 규칙을 교체할 때 체인의 역할이 분명해진다.

서블릿의 필터 체인은 각 필터가 다음 처리의 실행 여부를 정하는 사례다. 다음 필터 호출 전후에 작업을 수행할 수도 있으므로, 문의 분류 예제처럼 한 처리기에서 종료하는 규칙은 각 체인의 계약에서 결정한다. [Java Servlet FilterChain](https://docs.oracle.com/javaee/7/api/javax/servlet/FilterChain.html)
