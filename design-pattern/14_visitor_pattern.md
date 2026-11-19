# Visitor Pattern

여러 종류의 객체를 순회하면서 분류, 계산, 출력 같은 작업을 수행할 때, 객체 종류별 처리 코드를 방문자에 모을 수 있다. 요소 객체는 방문자를 받아들이는 `accept`를 제공하고, 방문자는 요소 유형마다 필요한 작업을 구현한다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 상품 유형별 배송비와 표시 이름 계산하기

```java
import java.util.List;

public class VisitorExample {
    interface Item {
        <R> R accept(ItemVisitor<R> visitor);
    }

    interface ItemVisitor<R> {
        R visit(PrintedBook book);
        R visit(Ebook ebook);
    }

    record PrintedBook(int grams) implements Item {
        @Override
        public <R> R accept(ItemVisitor<R> visitor) {
            return visitor.visit(this);
        }
    }

    record Ebook(String format) implements Item {
        @Override
        public <R> R accept(ItemVisitor<R> visitor) {
            return visitor.visit(this);
        }
    }

    static final class ShippingFee implements ItemVisitor<Integer> {
        public Integer visit(PrintedBook book) {
            return book.grams() > 500 ? 5_000 : 3_000;
        }

        public Integer visit(Ebook ebook) {
            return 0;
        }
    }

    static final class DeliveryLabel implements ItemVisitor<String> {
        public String visit(PrintedBook book) {
            return "PARCEL";
        }

        public String visit(Ebook ebook) {
            return "DOWNLOAD " + ebook.format();
        }
    }

    public static void main(String[] args) {
        List<Item> items = List.of(new PrintedBook(650), new Ebook("EPUB"));
        var feeVisitor = new ShippingFee();
        var labelVisitor = new DeliveryLabel();
        var fees = items.stream().map(item -> item.accept(feeVisitor)).toList();
        var labels = items.stream().map(item -> item.accept(labelVisitor)).toList();
        if (!fees.equals(List.of(5_000, 0))
                || !labels.equals(List.of("PARCEL", "DOWNLOAD EPUB"))) {
            throw new AssertionError("Unexpected visitor results");
        }
    }
}
```

배송비는 5,000원과 0원이고, 표시 이름은 각각 `PARCEL`과 `DOWNLOAD EPUB`이다. 먼저 실제 요소 유형에 맞는 `accept`가 호출된다. 각 `accept`에서 `this`의 타입에 해당하는 `visit` 오버로드를 선택하고, 실제 방문자 객체의 구현을 호출한다. 요소 유형과 방문자 유형이 함께 결과를 결정하는 이 구성을 이중 디스패치라고 한다.

## 어떤 변경이 자주 일어나는지 확인하기

상품 유형이 안정되고 처리 작업이 늘어나는 구조라면 방문자를 추가해 작업을 확장할 수 있다. 반면 요소 유형을 추가하면 방문자 인터페이스와 기존 방문자의 처리도 함께 늘어난다. [Iterator](24_iterator_pattern.md)는 요소에 접근하는 순서를 제공하고, Visitor는 접근한 요소의 종류에 맞는 연산을 수행한다.
