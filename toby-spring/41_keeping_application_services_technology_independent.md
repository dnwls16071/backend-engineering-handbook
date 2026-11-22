# Keeping Application Services Technology Independent

애플리케이션 서비스가 사용하는 명령·결과 타입은 유스케이스의 용어를 사용한다. HTTP 요청, JPA EntityManager 같은 기술 타입의 변환은 외부 어댑터가 수행할 수 있다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Martin Fowler · Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html)

## 1. 코드 경계와 실행 경계를 비교한다

웹과 배치의 입력을 같은 주문 생성 명령으로 변환하고, 서비스를 실행한 결과를 호출자별 응답으로 바꾼다. 저장은 업무 포트를 거쳐 교체 가능한 어댑터로 연결한다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html)

## 2. 테스트에서 바깥 구현을 교체한다

서비스의 테스트는 메모리 저장 대역이나 고정 시간으로 실행한다. DB 쿼리와 트랜잭션, HTTP 오류 매핑은 각 어댑터와 실제 구성의 테스트에서 따로 확인한다. [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
