# Builder Pattern

여러 단계가 필요한 객체 생성에서, 만드는 과정과 결과의 표현을 분리한다. 같은 생성 절차를 유지하면서 텍스트 보고서와 구조화된 보고서처럼 서로 다른 결과 형식을 만들 수 있다. 빌더는 각 단계에서 필요한 데이터를 받고 최종 표현을 조립한다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 같은 절차로 다른 보고서 형태 만들기

```java
import java.util.ArrayList;
import java.util.List;

public class BuilderExample {
    interface ReportBuilder<R> {
        void title(String title);
        void addLine(String line);
        R build();
    }

    record StructuredReport(String title, List<String> lines) {}

    static final class StructuredReportBuilder implements ReportBuilder<StructuredReport> {
        private String title;
        private final List<String> lines = new ArrayList<>();

        public void title(String value) {
            title = value;
        }

        public void addLine(String line) {
            lines.add(line);
        }

        public StructuredReport build() {
            return new StructuredReport(title, List.copyOf(lines));
        }
    }

    static final class TextReportBuilder implements ReportBuilder<String> {
        private final StringBuilder output = new StringBuilder();

        public void title(String title) {
            output.append(title);
        }

        public void addLine(String line) {
            output.append('\n').append(line);
        }

        public String build() {
            return output.toString();
        }
    }

    static <R> R buildDailyReport(ReportBuilder<R> builder) {
        builder.title("Daily orders");
        builder.addLine("Paid: 3");
        return builder.build();
    }

    public static void main(String[] args) {
        String text = buildDailyReport(new TextReportBuilder());
        StructuredReport structured = buildDailyReport(new StructuredReportBuilder());
        if (!text.equals("Daily orders\nPaid: 3")
                || !structured.equals(new StructuredReport("Daily orders", List.of("Paid: 3")))) {
            throw new AssertionError("Unexpected report");
        }
    }
}
```

`buildDailyReport`가 제목 설정과 항목 추가의 순서를 정한다. 호출자는 선택한 빌더에 따라 줄바꿈이 있는 문자열 또는 제목과 항목 목록을 받는다. 구조화된 결과의 항목 목록은 생성 시점의 값으로 복사된다.

## 적용할 때 확인할 점

필수 값과 선택 값이 많아 생성 단계가 복잡하면 빌더에서 유효성을 검사하고, 완성된 객체만 반환하도록 설계한다. 메서드 체이닝은 빌더의 입력을 편하게 적는 API 형식이다. GoF 예제의 중심에는 같은 생성 과정에서 여러 표현을 얻는 구조가 있으며, 한 제품의 선택적 인자를 모으는 Java 빌더에도 단계적 생성이라는 아이디어를 적용할 수 있다. [Abstract Factory](12_abstract_factory_pattern.md)는 함께 쓰이는 제품군의 생성을 다룬다.
