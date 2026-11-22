# Introducing a Service Interface

서비스가 환율 제공자와 통신할 때 필요한 계약을 ExRateProvider로 드러낸다. 웹 기반 제공자와 테스트 대역은 같은 계약에 맞는 구현이 된다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf)

## 1. 사용자가 필요로 하는 계약을 선언한다

환율을 요청하는 쪽에 필요한 것은 통화 쌍, 기준과 상대 통화의 의미, 조회된 비율과 실패 규약이다. 예시 계약에는 HTTP 응답 타입과 JSON 형식을 전달할 필요가 없다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Liskov·Wing · Behavioral Subtyping](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf)

## 2. 교체 가능한 구현인지 확인한다

고정 환율을 반환하는 구현이나 외부 조회 구현으로 교체하고 결제 계산 결과를 비교한다. 계약에는 필요한 업무 정보만 남겨 변경되는 제공자 세부사항을 구현 안에서 처리한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)
