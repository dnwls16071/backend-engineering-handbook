# Introducing an Application Service

OrderService는 입력을 받아 주문을 구성하고 도메인 규칙을 실행한 뒤 저장한다. 웹 컨트롤러가 직접 저장소를 호출하던 흐름에서는 유스케이스를 한 곳으로 모을 수 있다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html)

## 1. 유스케이스의 순서를 표현한다

주문 접수의 예는 요청 변환 → 고객·상품 확인 → 주문 생성 → 저장 → 결과 반환이다. 값과 상태 전이 검증은 도메인에 맡기고 서비스가 각 단계를 조정한다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html)

## 2. 필요한 실패를 서비스 경계에서 확인한다

상품을 준비할 수 없거나 중간 저장이 실패한 경우를 각각 시험한다. 동일한 업무를 웹과 배치에서 호출해도 조정과 트랜잭션 규칙이 같은 진입점으로 모이게 한다. [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
