# Injecting ApiExecutor as a Callback

실행 정책이 호출마다 바뀐다면 ApiExecutor를 메서드 인자로 전달할 수 있다. 객체 생성 시 고정하는 생성자 주입과 선택 시점이 다르다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html)

## 1. 호출에 필요한 전략을 전달한다

템플릿이 URI를 받고 전달된 실행자 콜백을 호출하도록 구성한다. 콜백이 사용할 요청 정보를 명시하고, HTTP 구현의 세부사항을 공통 실행 흐름 밖에 둔다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 2. 반환값과 실패 규약을 맞춘다

고정 응답과 타임아웃을 발생시키는 콜백을 각각 전달해 확인한다. 공통 흐름에서 실패를 처리할 수 있는 범위와 호출자의 몫을 구분한다. [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html)
