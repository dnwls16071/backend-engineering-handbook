# Using Spring Templates and Callbacks

Spring 템플릿은 공통 제어 흐름을 제공하고 호출자가 변하는 부분을 전달할 수 있게 한다. 예제의 HTTP 템플릿과 데이터 접근 템플릿이 같은 부분과 다른 부분을 비교한다. [Spring 6.2 JdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html) · [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 1. 업무에 맞는 Spring 도구를 고른다

| 도구 | 공통 제어 흐름과 달라지는 부분 | 근거 |
| --- | --- | --- |
| JdbcTemplate | 커넥션과 JDBC 자원을 관리하고 SQL 인자·RowMapper를 사용한다. | [Spring 6.2 JdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html) |
| TransactionTemplate | 트랜잭션 경계 안에서 전달한 콜백을 실행한다. | [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html) |
| RestClient / RestTemplate | 동기 HTTP 요청에서 URI·헤더·바디·응답 변환을 조합한다. | [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) |

## 2. 애플리케이션 인터페이스를 유지한다

범용 클라이언트를 직접 만든 코드가 있다면 프레임워크 도구의 오류·변환·자원 정책을 비교한다. 업무 코드는 환율이나 주문 저장 계약을 사용하고 실제 도구는 어댑터가 선택할 수 있게 한다. [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture?trk=public_post_comment-text) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html) · [Spring 6.2 JdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html)
