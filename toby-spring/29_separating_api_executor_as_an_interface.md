# Separating ApiExecutor as an Interface

ApiExecutor를 분리하면 환율 어댑터는 요청 실행 규약을 사용하고 실제 HTTP 기술은 구현 클래스가 선택한다. 테스트에서는 응답을 직접 돌려주는 대역을 연결할 수 있다. [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)

## 1. 실행자의 입력과 출력 범위를 정한다

예제 계약은 URI를 받아 상태 규약을 적용한 응답 본문을 반환한다. 실제 구현은 HttpClient를 재사용할 수 있으며 연결·요청 제한과 헤더 설정은 실행자 쪽에 둔다. [Java 21 HttpClient](https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpClient.html) · [Java 21 HttpRequest.Builder](https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpRequest.Builder.html)

## 2. 환율 파싱과 HTTP 설정을 별도 검사한다

응답 문자열로부터 비율을 계산하는 검사에는 실행자 대역을 넣는다. 네트워크 클라이언트 설정, 상태 검사와 요청 헤더는 실제 실행자 경계에서 검증한다. [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html)
