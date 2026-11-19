# Composite Pattern

개별 상품과 여러 상품으로 이루어진 묶음에 같은 방식으로 가격을 물을 수 있다. Composite는 잎과 하위 항목을 가진 그룹이 공통 연산을 구현하도록 한다. 그룹은 자식에게 연산을 위임하고 결과를 합친다.

## 트리의 각 항목에 같은 연산 적용하기

예제의 `MenuItem`은 가격 조회만 제공한다. 단품은 자신의 가격을 반환하고, 세트는 구성 항목의 가격을 더한다. 세트 안에 또 다른 세트가 들어가도 호출부의 사용법은 같다. [GoF의 Composite 패턴](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

```java
import java.util.List;

class CompositeExample {
    interface MenuItem {
        long priceWon();
    }

    record Dish(long priceWon) implements MenuItem {}

    record MealSet(List<MenuItem> items) implements MenuItem {
        MealSet {
            items = List.copyOf(items);
        }

        @Override
        public long priceWon() {
            long total = 0;
            for (MenuItem item : items) {
                total = Math.addExact(total, item.priceWon());
            }
            return total;
        }
    }

    public static void main(String[] args) {
        MenuItem sideSet = new MealSet(List.of(new Dish(2_000), new Dish(1_000)));
        MenuItem meal = new MealSet(List.of(new Dish(6_000), sideSet));
        if (meal.priceWon() != 9_000) {
            throw new AssertionError("Nested menu total should be 9,000 won");
        }
    }
}
```

6,000원짜리 주 메뉴와 3,000원짜리 하위 세트의 합은 9,000원이다. 공통 연산을 가격 조회로 제한하면 자식을 관리하는 책임을 그룹에 둘 수 있다.

## 적용 기준

폴더와 파일, 메뉴와 하위 메뉴처럼 부분과 전체를 같은 경계로 읽을 때 유용하다. 가변 트리에서는 중첩 깊이, 부모 변경, 순환 방지 규칙을 정한다. [Decorator](16_decorator_pattern.md)는 감싼 대상의 동작에 기능을 더하고, Composite는 여러 자식의 결과를 하나로 모은다.
