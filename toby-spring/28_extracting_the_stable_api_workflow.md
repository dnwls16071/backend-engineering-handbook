# Extracting the Stable API Workflow

공통 흐름은 요청 실행, 응답 획득, 결과 변환의 순서를 표현한다. 이 순서가 여러 제공자에게 공통인지 두 응답 예로 확인한다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 1. 공통 순서를 한 곳에 모은다

호출자가 URI를 넘기면 실행 메서드가 응답을 받고 추출 로직으로 전달하는 예다. 타임아웃이나 오류 변환을 공통 정책으로 두려면 호출자마다 의미가 같은지 비교한다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Java 21 HttpRequest.Builder](https://docs.oracle.com/en/java/javase/21/docs/api/java.net.http/java/net/http/HttpRequest.Builder.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 2. 공통 정책과 개별 정책을 구분한다

응답 코드 404의 의미처럼 제공자마다 달라지는 규칙은 어댑터가 해석한다. 공통 흐름은 변경 없는 실행 순서를 맡고, 개별 정책은 각 구현에서 검증한다. [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) · [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html)
