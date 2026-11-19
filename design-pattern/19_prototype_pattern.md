# Prototype Pattern

비슷한 설정으로 객체를 반복해서 만들 때는 초기값을 담은 원형 객체를 복제하고 필요한 값만 바꿀 수 있다. 생성 코드는 원형을 전달받고, 그 객체가 제공하는 복제 연산을 호출한다.

## 복제 규칙을 원형에 두기

원형은 새 객체에 어떤 값을 복사하고 어떤 값을 공유할지 결정한다. 아래 예제에서는 보고서 템플릿의 열 목록을 복사한다. 열 이름은 불변 문자열이므로 공유할 수 있고, 열을 추가하는 목록은 템플릿별로 독립시킨다. [GoF의 Prototype 패턴](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

```java
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

class PrototypeExample {
    static final class ReportTemplate {
        private final List<String> columns;

        ReportTemplate(List<String> columns) {
            this.columns = new ArrayList<>(List.copyOf(columns));
        }

        ReportTemplate copy() {
            return new ReportTemplate(columns);
        }

        void addColumn(String column) {
            columns.add(Objects.requireNonNull(column, "column"));
        }

        List<String> columns() {
            return List.copyOf(columns);
        }
    }

    public static void main(String[] args) {
        var template = new ReportTemplate(List.of("결제일", "금액"));
        var monthly = template.copy();
        monthly.addColumn("월");
        if (!template.columns().equals(List.of("결제일", "금액"))
                || !monthly.columns().equals(List.of("결제일", "금액", "월"))) {
            throw new AssertionError("The copy must own its column list");
        }
    }
}
```

월간 보고서에 열을 추가해도 원형의 열 목록은 두 개다. 가변 요소가 목록 안에 들어 있다면 바깥 목록만 복사해도 요소의 참조는 공유된다. 복제 후 각 객체가 독립적으로 수정해야 하는 범위까지 복사하고, ID나 열린 자원처럼 새로 할당해야 할 값의 처리도 정한다.

## 적용 기준

초기화가 복잡하고 같은 설정의 변형을 반복해서 만들 때 적합하다. 복제 범위가 넓거나 원형에 가변 의존성이 많으면 복사 비용과 공유할 참조를 검토한다. [Builder](15_builder_pattern.md)는 생성 단계를 통해 값을 조립하고, Prototype은 이미 만들어진 객체의 상태에서 시작한다.
