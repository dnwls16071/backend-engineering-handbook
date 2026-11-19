# Abstract Factory Pattern

추상 팩토리 패턴은 함께 사용해야 하는 제품의 조합을 하나의 생성 계약으로 제공한다. 웹과 무인 단말에서 영수증을 보여 줄 때, 영수증 제목과 금액의 표시 방식은 채널별로 맞춰야 한다.

## 구조와 선택 기준

- `ReceiptFactory`는 제목과 금액을 만드는 두 연산을 제공한다.
- 구체 팩토리인 `WebReceiptFactory`와 `TerminalReceiptFactory`는 각 채널에 맞는 제품군을 생성한다.
- 영수증을 표시하는 코드는 받은 팩토리에서 두 제품을 얻어 사용한다. 구체 제품을 선택하는 책임은 팩토리에 있다.

일관된 제품 조합을 여러 곳에서 쓰고 조합 전체를 교체해야 할 때 적합하다. 새로운 제품군은 팩토리 구현으로 추가할 수 있다. 제목과 금액 외에 제품 종류가 늘면 공통 인터페이스와 여러 팩토리 구현이 함께 바뀔 수 있다. [팩토리 메서드](08_factory_method_pattern.md)는 상위 흐름에서 호출할 생성 메서드를 하위 타입이 재정의하는 구조다.

## Java 17 예제

```java
class AbstractFactoryExample {
    interface ReceiptTitle {
        String text();
    }

    interface ReceiptAmount {
        String format(int won);
    }

    interface ReceiptFactory {
        ReceiptTitle createTitle();
        ReceiptAmount createAmount();
    }

    static final class WebReceiptFactory implements ReceiptFactory {
        @Override
        public ReceiptTitle createTitle() {
            return () -> "Web receipt";
        }

        @Override
        public ReceiptAmount createAmount() {
            return won -> "₩" + won;
        }
    }

    static final class TerminalReceiptFactory implements ReceiptFactory {
        @Override
        public ReceiptTitle createTitle() {
            return () -> "TERMINAL RECEIPT";
        }

        @Override
        public ReceiptAmount createAmount() {
            return won -> "KRW " + won;
        }
    }

    static String render(ReceiptFactory factory, int won) {
        ReceiptTitle title = factory.createTitle();
        ReceiptAmount amount = factory.createAmount();
        return title.text() + ": " + amount.format(won);
    }

    public static void main(String[] args) {
        if (!render(new WebReceiptFactory(), 1_200).equals("Web receipt: ₩1200")
                || !render(new TerminalReceiptFactory(), 1_200)
                        .equals("TERMINAL RECEIPT: KRW 1200")) {
            throw new AssertionError("Use matching receipt products for each channel");
        }
    }
}
```

제목과 금액 표기가 팩토리 단위로 바뀐다. 표시 로직은 같은 `render` 흐름을 사용한다.

참고 [Design Patterns · Abstract Factory](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)
