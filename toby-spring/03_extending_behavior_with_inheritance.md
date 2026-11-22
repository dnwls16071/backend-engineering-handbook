# Extending Behavior with Inheritance

상속을 쓰면 부모 클래스가 제공하는 흐름 중 일부를 하위 클래스에서 바꿀 수 있다. 부모가 기대하는 입력과 반환, 오류 계약을 하위 구현도 충족해야 한다. [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf) · [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html)

## 1. 상속이 제공하는 확장 지점을 정한다

부모의 전체 흐름에서 환율 조회용 메서드만 재정의하는 예를 생각한다. 재정의할 메서드의 인자와 반환, 실패 조건을 명시하고 나머지 단계는 부모에서 유지한다. [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf) · [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html)

## 2. 상속이 추가하는 결합을 확인한다

하위 클래스가 부모의 호출 순서나 내부 상태를 알아야 하면 양쪽 수정이 엮인다. 같은 클래스 안에서 환율 정책을 실행 시점에 바꿔야 한다면 협력 객체를 전달하는 구성을 비교한다. [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)
