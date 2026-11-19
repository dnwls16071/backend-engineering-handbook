# Template Method Pattern

템플릿 메서드는 알고리즘의 단계와 실행 순서를 상위 클래스에 두고, 달라지는 단계를 하위 클래스에 맡기는 행동 패턴이다. Java에서 전체 절차를 `final` 메서드로 정의하면 하위 클래스가 공통 순서를 그대로 사용한다. [GoF의 Template Method](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610) · [Java 언어 명세의 final 메서드](https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.4.3.3)

## 어떤 문제를 푸는가

여러 매출 보고서에서 헤더와 푸터 형식은 같고 본문만 달라진다고 하자. 보고서마다 전체 문자열을 조립하면 공통 형식을 바꿀 때 각 구현을 찾아 수정해야 한다. 상위 클래스가 조립 순서를 만들고 보고서별 클래스는 본문을 채우도록 한다.

## Java 17 예제

```java
public class TemplateMethodExample {
    abstract static class Report {
        final String render() {
            return "[Sales]\n" + body() + "\n[End]";
        }

        protected abstract String body();
    }

    static final class DailyReport extends Report {
        @Override
        protected String body() {
            return "Day: 3 sales";
        }
    }

    static final class WeeklyReport extends Report {
        @Override
        protected String body() {
            return "Week: 21 sales";
        }
    }

    public static void main(String[] args) {
        String daily = new DailyReport().render();
        String weekly = new WeeklyReport().render();
        if (!daily.equals("[Sales]\nDay: 3 sales\n[End]")
                || !weekly.equals("[Sales]\nWeek: 21 sales\n[End]")) {
            throw new AssertionError("Incorrect report layout");
        }
        System.out.println(daily);
        System.out.println(weekly);
    }
}
```

일간 보고서와 주간 보고서에 공통 헤더 `[Sales]`와 푸터 `[End]`가 출력되고, 가운데 줄에 각 보고서의 본문이 들어간다. `body`는 구현이 필수인 단계다. 기본 동작을 제공하는 선택적 단계는 훅 메서드로 둘 수 있다.

## 적용할 때 볼 점

- 변형이 적고 단계의 실행 순서가 안정적이라면 공통 절차를 한곳에 둘 수 있다.
- 하위 클래스는 상위 클래스가 메서드를 호출하는 시점과 조건에 의존한다. 단계 순서나 훅 계약을 바꾸면 하위 구현도 함께 검토한다.
- 조합으로 절차 안의 일부 연산을 주입할 수도 있다. 상위 클래스가 변형 단계를 호출하게 하려면 템플릿 메서드가 맞고, 정책을 독립적으로 조합하거나 실행 중 선택해야 한다면 전략을 검토한다. [Strategy Pattern](02_strategy_pattern.md)
