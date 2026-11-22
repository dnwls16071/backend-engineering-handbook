# Refactoring WebApiExRateProvider

환율 웹 어댑터를 URI 생성, API 호출, 응답의 환율 추출, 오류 변환 순서로 읽는다. 각 단계가 무엇을 바꾸는지 파악한 뒤 작은 단위로 추출한다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 1. 외부 어댑터의 관찰 가능한 계약을 잡는다

정해진 응답에서 어떤 환율을 반환하는지와 실패 시 어떤 오류를 노출하는지 먼저 테스트한다. 정상 사례, 형식 오류, HTTP 오류를 고정 응답으로 재현한다. [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 2. 변경 단계마다 같은 계약을 확인한다

먼저 이름 붙은 메서드로 흐름을 읽을 수 있게 한다. 그 뒤 구현이 바뀌는 부분을 별도 협력자로 이동하고, 외부 클라이언트의 세부 예외는 어댑터 경계에서 해석한다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)
