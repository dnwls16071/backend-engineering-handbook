# Extracting Exchange Rates with a Callback

ExRateExtractor는 응답을 애플리케이션의 환율 값으로 변환하는 콜백이다. HTTP 호출자가 같아도 API마다 다른 응답 형식을 처리할 수 있다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text)

## 1. 추출 로직의 입력과 오류를 정한다

응답의 필수 필드, 기준 통화와 상대 통화, 소수 표현과 누락 데이터 규칙을 정한다. 문자를 BigDecimal로 바꿀 때는 부동소수점 변환을 경유하는 것과 차이가 있으므로 입력 규약에 맞춘다. [Java 21 BigDecimal](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 2. 추출기를 응답 표본으로 검증한다

정상 필드, 누락, 잘못된 숫자와 기대와 다른 통화의 응답으로 검사한다. 추출기의 실패는 명시적으로 표현하고 승인된 환율처럼 후속 계산에 전달되지 않게 한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Spring 6.2 Client REST Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/spring-mvc-test-client.html) · [Java 21 BigDecimal](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html)
