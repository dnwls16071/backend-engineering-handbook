# Separating Concerns in Payment Processing

결제 준비에서 금액 계산, 환율 서버 호출, 객체 조립은 서로 다른 이유로 바뀐다. 바뀌는 이유를 기준으로 메서드나 객체의 경계를 잡는다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html)

## 1. 업무 규칙과 외부 작업을 분리한다

금액 계산은 전달된 금액과 환율로 결과를 만든다. 외부 조회 코드는 URI와 응답을 해석하고, 구성 코드는 어떤 조회 구현을 사용할지 정한다. 이름은 계산 대상, 외부 경계, 선택 책임을 설명하도록 붙인다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)

## 2. 변경 시나리오로 경계를 검증한다

환율 제공자가 바뀔 때 계산 규칙이 그대로인지, 계산이 바뀔 때 네트워크 코드를 열어야 하는지 확인한다. 서로 다른 이유의 변경이 계속 같은 곳으로 모이면 책임을 다시 나눈다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)
