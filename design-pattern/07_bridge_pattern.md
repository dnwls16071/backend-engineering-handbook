# Bridge Pattern

브리지 패턴은 기능을 표현하는 추상화와 그 기능을 실행하거나 표시하는 구현을 각각 발전시킬 수 있게 연결한다. 보고서 종류가 요약형과 상세형으로 늘어나고 출력 형식이 일반 텍스트와 Markdown으로 나뉘면, 각 조합에 별도의 클래스를 만들 때 변경 지점이 빠르게 늘어난다.

## 구조와 선택 기준

- 추상화인 `Report`는 보고서 작성 흐름을 제공하고 출력 형식은 `Renderer`에 위임한다.
- 확장된 추상화인 `SummaryReport`와 `DetailedReport`는 각각 어떤 내용을 담을지 정한다.
- 구체 구현은 같은 제목과 본문을 다른 형식으로 표현한다. 보고서와 출력기 중 한쪽을 추가해도 기존의 다른 분류를 그대로 조합할 수 있다.

두 축이 실제로 독립적으로 바뀔 때 효과가 크다. 축 하나만 변하는 기능에서는 타입과 위임 계층의 비용을 함께 검토한다. [어댑터](06_adapter_pattern.md)는 이미 존재하는 인터페이스 사이의 호환성을 맞춘다. 브리지는 설계 단계에서 서로 다른 변화의 축을 분리한다.

## Java 17 예제

```java
import java.util.List;

class BridgeExample {
    interface Renderer {
        String render(String title, List<String> lines);
    }

    abstract static class Report {
        private final Renderer renderer;

        Report(Renderer renderer) {
            this.renderer = renderer;
        }

        final String publish() {
            return renderer.render("Orders", lines());
        }

        protected abstract List<String> lines();
    }

    static final class SummaryReport extends Report {
        SummaryReport(Renderer renderer) {
            super(renderer);
        }

        @Override
        protected List<String> lines() {
            return List.of("Total: 2");
        }
    }

    static final class DetailedReport extends Report {
        DetailedReport(Renderer renderer) {
            super(renderer);
        }

        @Override
        protected List<String> lines() {
            return List.of("Order A", "Order B");
        }
    }

    public static void main(String[] args) {
        Renderer plain = (title, lines) -> title + "\n" + String.join("\n", lines);
        Renderer markdown = (title, lines) -> "# " + title + "\n- " + String.join("\n- ", lines);

        if (!new SummaryReport(plain).publish().equals("Orders\nTotal: 2")
                || !new SummaryReport(markdown).publish().equals("# Orders\n- Total: 2")
                || !new DetailedReport(markdown).publish().equals("# Orders\n- Order A\n- Order B")) {
            throw new AssertionError("Report content and format should vary independently");
        }
    }
}
```

같은 요약 보고서를 두 형식으로 출력하고, 같은 Markdown 출력기를 상세 보고서에도 적용할 수 있다.

참고 [Design Patterns · Bridge](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)
