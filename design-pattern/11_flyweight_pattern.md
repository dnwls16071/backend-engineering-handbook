# Flyweight Pattern

플라이웨이트 패턴은 많은 객체가 반복해서 가지는 상태를 공유해 저장 비용을 줄인다. 화면에 라벨을 수천 개 배치할 때 글꼴과 크기 조합은 반복되는 반면, 내용과 좌표는 라벨마다 달라질 수 있다.

## 구조와 선택 기준

- 내재 상태는 객체 사이에서 공유할 값이다. 예제에서는 불변인 `GlyphStyle`에 글꼴과 크기를 둔다.
- 외재 상태는 사용 위치가 결정하는 값이다. 라벨의 내용과 좌표는 각 `Label`이 가진다.
- 풀은 같은 내재 상태에 대해 동일한 스타일 객체를 돌려준다. 스타일에 위치별 상태를 저장하면 한 사용처의 변경이 다른 사용처에 영향을 줄 수 있다.

반복되는 상태가 크고 조합의 수가 적을수록 이점이 크다. 공유 키가 계속 늘어나면 풀의 메모리도 늘기 때문에 키의 범위와 유지 기간을 정한다. [싱글턴](04_singleton_pattern.md)은 특정 범위에서 한 인스턴스를 제공한다. 플라이웨이트 풀은 공유할 상태의 종류마다 인스턴스를 둘 수 있다.

## Java 17 예제

```java
import java.util.HashMap;
import java.util.Map;

class FlyweightExample {
    record GlyphStyle(String font, int size) {}

    record Label(String text, int x, int y, GlyphStyle style) {}

    static final class StylePool {
        private final Map<GlyphStyle, GlyphStyle> styles = new HashMap<>();

        GlyphStyle get(String font, int size) {
            return styles.computeIfAbsent(new GlyphStyle(font, size), style -> style);
        }
    }

    public static void main(String[] args) {
        var pool = new StylePool();
        var first = new Label("Total", 10, 20, pool.get("Sans", 14));
        var second = new Label("Tax", 10, 40, pool.get("Sans", 14));
        var heading = new Label("Invoice", 0, 0, pool.get("Sans", 18));

        if (first.style() != second.style()
                || first.style() == heading.style()
                || first.y() == second.y()) {
            throw new AssertionError("Share equal styles while keeping label positions separate");
        }
    }
}
```

첫 두 라벨은 같은 스타일 인스턴스를 참조하고, 18pt 제목은 별도 스타일을 참조한다. 내용과 좌표는 각 라벨에 남아 있다.

참고 [Design Patterns · Flyweight](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)
