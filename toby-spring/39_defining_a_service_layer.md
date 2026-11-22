# Defining a Service Layer

서비스 계층은 호출자가 사용할 유스케이스 진입점이며, 업무 객체와 저장소의 작업 순서를 조정한다. 주문 접수 예를 통해 서비스와 도메인의 책임을 구분한다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html)

## 1. 애플리케이션 조정과 도메인 규칙을 나눈다

| 역할 | 주문 처리에서 맡는 일 | 근거 |
| --- | --- | --- |
| 애플리케이션 서비스 | 주문 생성 요청을 받아 필요한 객체를 찾고 저장 순서를 조정한다. | [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) |
| 도메인 객체 | 주문에서 허용되는 상태 전이와 값의 규칙을 지킨다. | [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html) |
| 저장 어댑터 | 영속 기술과 데이터 매핑의 구체 동작을 담당한다. | [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) |

## 2. 경계를 호출 결과에 드러낸다

호출자는 주문 ID나 업무 오류를 받는다. 유스케이스의 완료는 어떤 변경까지 저장했는지 설명할 수 있어야 하고, 트랜잭션 경계는 클라이언트 조작보다 서비스 단위로 잡는다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html)
