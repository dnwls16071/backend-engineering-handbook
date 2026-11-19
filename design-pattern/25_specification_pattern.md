# Specification Pattern

여러 화면이나 작업이 같은 업무 조건을 검사한다면 판정 규칙을 독립된 명세로 표현할 수 있다. 명세는 후보를 받아 충족 여부를 반환하며, 더 작은 조건을 결합해 검색이나 유효성 검증에서 재사용할 수 있다. [Eric Evans와 Martin Fowler의 Specifications](https://martinfowler.com/apsupp/spec.pdf)

## 후보와 판단 규칙 나누기

매장 수령 또는 당일 배송이 가능한 판매 상품을 찾는다고 하자. 판매하려면 재고가 있고 단종 상태가 아니어야 한다. 조건에 이름을 붙인 뒤 논리곱, 논리합, 부정으로 합친다.

```java
class SpecificationExample {
    record Product(int stock, boolean discontinued, boolean pickup, boolean sameDay) {}

    interface Specification<T> {
        boolean isSatisfiedBy(T candidate);

        default Specification<T> and(Specification<T> other) {
            return candidate -> isSatisfiedBy(candidate) && other.isSatisfiedBy(candidate);
        }

        default Specification<T> or(Specification<T> other) {
            return candidate -> isSatisfiedBy(candidate) || other.isSatisfiedBy(candidate);
        }

        default Specification<T> not() {
            return candidate -> !isSatisfiedBy(candidate);
        }
    }

    public static void main(String[] args) {
        Specification<Product> hasStock = product -> product.stock() > 0;
        Specification<Product> discontinued = Product::discontinued;
        Specification<Product> pickup = Product::pickup;
        Specification<Product> sameDay = Product::sameDay;
        var eligible = hasStock.and(discontinued.not()).and(pickup.or(sameDay));

        if (!eligible.isSatisfiedBy(new Product(2, false, false, true))
                || !eligible.isSatisfiedBy(new Product(1, false, true, false))
                || eligible.isSatisfiedBy(new Product(0, false, true, true))
                || eligible.isSatisfiedBy(new Product(3, true, true, false))) {
            throw new AssertionError("Unexpected eligibility");
        }
    }
}
```

판매 중이며 재고가 있는 상품은 둘 중 하나의 수령 방식만 만족해도 통과한다. 재고가 없거나 단종된 상품은 제외된다. 조건을 재사용할 때는 어떤 시점의 재고를 기준으로 판단하는지, 판단과 실제 상태 변경을 어떤 경계에서 처리하는지도 정한다.

## 적용 기준

[Strategy](02_strategy_pattern.md)는 선택한 작업을 수행하는 방법을 교체하는 데 쓰고, Specification은 후보가 조건을 충족하는지 판정하는 책임에 초점을 둔다. Java 람다로 구현한 위 명세는 메모리에서 평가한다. 데이터베이스 필터로도 쓰려면 쿼리 조건으로 변환 가능한 표현을 정하고, 메모리 평가와 DB 평가의 의미가 맞는지 검증한다.
