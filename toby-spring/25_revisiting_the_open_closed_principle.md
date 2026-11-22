# Revisiting the Open–Closed Principle

개방 폐쇄 원칙을 적용할 대상을 먼저 정한다. 이 예에서 외부 환율 응답 형식과 호출 방법은 바뀔 수 있고, 결제 준비의 계산 계약은 그대로 둘 수 있다. [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)

## 1. 변화 가능성이 확인된 지점에 구조를 둔다

새 제공자를 추가할 때 계산 코드가 바뀌면 계약이 외부 구현에 새어 나오는지 본다. 환율 조회와 응답 추출을 협력자로 두고, 외부 기술에 관한 분기를 해당 경계 안에서 처리한다. [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 2. 같은 테스트로 기존 결과를 확인한다

리팩터링 전후 같은 입력·결과를 검사한다. 바뀐 요구를 추가하는 작업과 기존 코드의 책임을 나누는 작업을 구분하면 테스트 실패 원인을 좁힐 수 있다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)
