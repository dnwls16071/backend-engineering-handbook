# Refactoring for Abstraction and Cohesion

[코드 다듬기](04_refining_code_for_maintainability.md)에서 확인한 동작 보존을 주문 포장 예제에 적용한다. 포장 명세에는 주문 수량의 합계, 총무게, 박스 종류가 들어간다. 예제에서는 총무게가 2,000g 이하면 소형 박스를 사용한다. 주문 항목은 하나 이상이라고 가정한다.

## 1. 리팩터링 전에 확인할 동작 정하기

기존 구현은 주문 항목을 순회하면서 수량과 무게를 합산하고, 박스를 고른 뒤 포장 명세를 만든다. 먼저 호출자가 받는 결과를 구체적으로 적는다. 박스 기준 바로 아래, 기준과 같은 무게, 기준 바로 위를 확인하면 비교 연산의 경계가 드러난다.

| 주문 항목의 총무게 | 포장 명세의 박스 종류 |
| --- | --- |
| 1,999g | `SMALL` |
| 2,000g | `SMALL` |
| 2,001g | `LARGE` |

박스 종류와 함께 전체 수량과 무게도 검증한다. 그래야 메서드를 나누다가 수량이 두 개 이상인 항목의 무게를 잘못 계산하는 일을 발견할 수 있다. [Martin Fowler의 리팩터링 정의](https://martinfowler.com/bliki/DefinitionOfRefactoring.html)

## 2. 추상화 수준을 맞추기

포장 흐름은 출고할 물품의 수량과 무게를 구한 뒤 박스를 골라 명세를 만드는 순서로 읽힌다. 순회와 곱셈을 하나의 연산으로 추출해 이름을 붙이면 상위 메서드에서 이 단계들이 보인다. 계산을 검토할 때는 추출한 메서드를 열어 항목의 수량과 단위 무게를 확인한다. [Martin Fowler의 Extract Function](https://refactoring.com/catalog/extractFunction.html)

## 3. 객체의 책임과 응집도 살펴보기

추출한 연산이 어느 데이터를 주로 사용하고 어떤 요구에서 함께 바뀌는지 본다. 수량과 무게를 합산하는 연산을 출고 내용물인 `ShipmentContents`에 둔다. 박스 분류 기준은 포장 정책인 `BoxPolicy`에 둔다. `Packing`은 이 결과를 조합해 포장 명세를 반환한다. 책임을 나눈 기준은 포장 단계에서 각 타입이 아는 정보와 변경 이유다. [Martin Fowler의 Move Function](https://refactoring.com/catalog/moveFunction.html) · [Robert C. Martin의 단일 책임 원칙](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html)

## 4. 관점에 맞는 추상화 선택하기

같은 주문 항목도 출고 담당자에게는 수량과 무게로, 구매자에게는 수량과 단가로 읽힌다. 예제에서는 주문 항목을 공통 입력으로 두고 각 흐름에 필요한 결과를 계산한다. 출고 관점의 `ShipmentContents`는 무게 합계를, 구매자 관점의 `CustomerOrderSummary`는 상품 소계를 표현한다.

```java
import java.util.List;

record OrderLine(int quantity, int unitPriceWon, int unitWeightGrams) {
    OrderLine {
        if (quantity <= 0 || unitPriceWon < 0 || unitWeightGrams <= 0) {
            throw new IllegalArgumentException("Invalid order line");
        }
    }
}

record PackingSlip(long totalUnits, long weightGrams, String boxCode) {}

final class PackingBefore {
    private static final long SMALL_BOX_LIMIT_GRAMS = 2_000;

    static PackingSlip prepare(List<OrderLine> lines) {
        long totalUnits = 0;
        long weightGrams = 0;
        for (OrderLine line : lines) {
            totalUnits = Math.addExact(totalUnits, line.quantity());
            weightGrams = Math.addExact(
                    weightGrams, (long) line.quantity() * line.unitWeightGrams());
        }
        String boxCode = weightGrams <= SMALL_BOX_LIMIT_GRAMS ? "SMALL" : "LARGE";
        return new PackingSlip(totalUnits, weightGrams, boxCode);
    }
}

record ShipmentContents(long totalUnits, long weightGrams) {
    static ShipmentContents from(List<OrderLine> lines) {
        long totalUnits = 0;
        long weightGrams = 0;
        for (OrderLine line : lines) {
            totalUnits = Math.addExact(totalUnits, line.quantity());
            weightGrams = Math.addExact(
                    weightGrams, (long) line.quantity() * line.unitWeightGrams());
        }
        return new ShipmentContents(totalUnits, weightGrams);
    }
}

final class BoxPolicy {
    private static final long SMALL_BOX_LIMIT_GRAMS = 2_000;

    static String selectFor(ShipmentContents contents) {
        return contents.weightGrams() <= SMALL_BOX_LIMIT_GRAMS ? "SMALL" : "LARGE";
    }
}

final class Packing {
    static PackingSlip prepare(List<OrderLine> lines) {
        var contents = ShipmentContents.from(lines);
        String boxCode = BoxPolicy.selectFor(contents);
        return new PackingSlip(contents.totalUnits(), contents.weightGrams(), boxCode);
    }
}

record CustomerOrderSummary(long subtotalWon) {
    static CustomerOrderSummary from(List<OrderLine> lines) {
        long subtotalWon = 0;
        for (OrderLine line : lines) {
            subtotalWon = Math.addExact(subtotalWon, (long) line.quantity() * line.unitPriceWon());
        }
        return new CustomerOrderSummary(subtotalWon);
    }
}
```

예를 들어 단가 10,000원·단위 무게 600g인 상품 2개와 단가 15,000원·단위 무게 800g인 상품 1개라면, 포장 명세는 3개, 2,000g, `SMALL`이다. 구매자용 상품 소계는 35,000원이다. 단가만 바꾸면 소계가 달라지고 포장 명세는 유지된다. 서로 다른 요구의 변경 범위를 테스트로 확인할 수 있다. [도메인 모델링 실습](03_object_oriented_domain_modeling_in_practice.md)

## 5. 핵심 키워드로 코드 검토하기

| 키워드 | 리뷰 질문 |
| --- | --- |
| 추상화 수준 | 상위 메서드에서 업무 단계가 보이고, 구체적인 계산을 어디에서 확인할지 알 수 있는가? |
| 책임과 응집도 | 같은 데이터와 변경 이유를 공유하는 연산이 함께 있는가? |
| 관점 | 이 흐름이 제공하는 정보가 실제 호출자의 질문에 맞는가? |
| 동작 보존 | 일반 입력과 경계 입력에서 리팩터링 전후의 결과가 같은가? |
