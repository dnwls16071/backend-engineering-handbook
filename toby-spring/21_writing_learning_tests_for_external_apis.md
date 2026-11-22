# Writing Learning Tests for External APIs

학습 테스트는 익숙하지 않은 라이브러리의 작은 동작을 실행해 확인한 결과를 남기는 데 쓸 수 있다. 예제로 HTTP 클라이언트의 상태 코드 처리 규약을 확인한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 1. 한 번에 하나의 동작을 확인한다

Spring RestClient와 로컬 테스트 응답을 사용해 성공 응답의 본문을 읽는지 먼저 검사한다. 이어서 HTTP 4xx일 때 기본 예외가 발생하는지, 상태 처리기를 지정하면 어떻게 달라지는지 검증한다. [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html)

## 2. 확인한 규약을 이후 변경에도 사용한다

실험의 라이브러리 버전, 호출 방법과 기대값을 코드에 명시한다. 외부 네트워크와 인증 없이는 재현할 수 없는 동작은 기대한 응답을 고정한 테스트와 별도로 다룬다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html)
