# Interpreter Pattern

반복해서 평가하는 규칙에 작은 문법이 있다면, 표현식을 트리로 구성하고 각 노드에 의미를 부여할 수 있다. Interpreter에서 말단 노드는 문맥의 값을 읽고, 합성 노드는 하위 표현식의 결과를 결합한다.

## 작은 배송 규칙 평가하기

당일 배송이 가능하고 상품이 깨지기 쉬운 품목이 아닐 때 간편 포장을 허용한다고 하자. 사용할 표현식은 `sameDay`, `fragile`, `not(expression)`, `and(left, right)`다. 예제는 표현식 트리를 코드로 직접 구성하고 각 배송 조건을 문맥으로 넘긴다. [GoF의 Interpreter 패턴](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

```java
class InterpreterExample {
    record DeliveryContext(boolean sameDay, boolean fragile) {}

    interface Expression {
        boolean evaluate(DeliveryContext context);
    }

    record SameDay() implements Expression {
        @Override
        public boolean evaluate(DeliveryContext context) {
            return context.sameDay();
        }
    }

    record Fragile() implements Expression {
        @Override
        public boolean evaluate(DeliveryContext context) {
            return context.fragile();
        }
    }

    record Not(Expression expression) implements Expression {
        @Override
        public boolean evaluate(DeliveryContext context) {
            return !expression.evaluate(context);
        }
    }

    record And(Expression left, Expression right) implements Expression {
        @Override
        public boolean evaluate(DeliveryContext context) {
            return left.evaluate(context) && right.evaluate(context);
        }
    }

    public static void main(String[] args) {
        Expression simplePacking = new And(new SameDay(), new Not(new Fragile()));
        if (!simplePacking.evaluate(new DeliveryContext(true, false))
                || simplePacking.evaluate(new DeliveryContext(true, true))
                || simplePacking.evaluate(new DeliveryContext(false, false))) {
            throw new AssertionError("Unexpected packing rule result");
        }
    }
}
```

같은 표현식을 여러 배송 조건에 적용할 수 있다. 문자열을 입력받는 설계라면 문자를 토큰으로 나누고 문법을 검사해 표현식 트리를 만드는 단계가 추가된다. 규칙이 많아지면 연산자 우선순위, 오류 메시지, 평가 비용도 검토한다.

## 적용 기준

문법이 작고 표현식을 여러 형태로 조립할 때 적합하다. 정해진 업무 조건을 합성해 후보가 적합한지 확인하는 데 초점이 있다면 [Specification](25_specification_pattern.md)으로 표현할 수 있다. Evans와 Fowler는 합성 명세의 구현 방법 중 하나로 Interpreter를 설명한다. [Specifications 원문](https://martinfowler.com/apsupp/spec.pdf)
