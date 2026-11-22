# Implementing JDBC Data Access

JdbcTemplate은 SQL과 매개변수, 결과 매핑을 받으며 연결과 예외 처리를 담당한다. 주문 저장 포트의 JDBC 구현 예에서는 JPA 구현과 동일한 업무 계약을 유지한다. [Spring 6.2 JdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html) · [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html)

## 1. SQL과 매핑을 어댑터 안에 둔다

값은 SQL 자리표시자의 매개변수로 전달하고, RowMapper가 결과 행을 주문 모델로 변환한다. 갱신 건수나 조회 결과 없음을 포트 계약에 맞게 해석한다. [Spring 6.2 JdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html) · [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html)

## 2. 현재 트랜잭션의 연결을 사용한다

트랜잭션 매니저와 JdbcTemplate이 같은 DataSource를 사용하도록 구성한다. 연결을 직접 관리하는 경우에는 Spring의 리소스 동기화 경로를 확인한다. 서로 다른 JDBC 연결에서 수행한 변경은 하나의 로컬 트랜잭션으로 자동 결합되지 않는다. [Spring 6.2 Managing Connections](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/connections.html) · [Spring 6.2 Resource Synchronization](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/tx-resource-synchronization.html) · [Java 21 JDBC Connection](https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/Connection.html)
