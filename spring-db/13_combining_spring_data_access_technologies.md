# Combining Spring Data Access Technologies

## 1. 저장소가 제공하는 계약에 따라 구현 고르기

상품 등록과 재고 수정에는 엔티티 변경 추적을 사용할 수 있다. 상품 검색에 조건 조합이 많을 때는 Querydsl을 붙이고, 집계 보고서나 DB 전용 SQL이 중심인 경우에는 JdbcTemplate이나 MyBatis로 조회를 작성할 수 있다. 한 서비스에서 이런 작업을 묶을 때는 트랜잭션 매니저와 데이터 소스가 어떻게 연결되는지 확인한다. [Spring Data JPA 3.5 · 저장소 확장](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/custom-implementations.html) · [Spring Framework 6.2 · JDBC Core](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html) · [MyBatis 3 · SQL 매핑](https://mybatis.org/mybatis-3/sqlmap-xml.html)

| 용도 | 예 |
| --- | --- |
| 일반 CRUD와 엔티티 변경 | Spring Data JPA 저장소 |
| 검색 조건의 조합 | Querydsl 기반 저장소 구현 또는 저장소 프래그먼트 |
| 구체적인 보고서 SQL | JdbcTemplate 또는 MyBatis와 조회용 DTO |

서비스가 정해진 JPA 저장소에 바로 의존하면 위임 코드가 줄어든다. 다른 구현으로 교체하거나 외부에 별도 계약을 제공해야 할 때는 애플리케이션 인터페이스를 두고 JPA 저장소를 어댑터에서 호출할 수 있다. 예를 들어 카탈로그 서비스를 그대로 유지하면서 검색 구현을 [JdbcTemplate](07_jdbc_template_named_parameters_and_dynamic_sql.md)에서 [Querydsl](12_querydsl_dynamic_jpa_queries.md)로 바꾸려면 검색 계약의 입력과 결과 타입을 먼저 고정한다. [Spring Data JPA 3.5 · 저장소 프래그먼트](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/custom-implementations.html)

## 2. 같은 트랜잭션에서 JPA와 SQL 사용하기

`JpaTransactionManager`는 JPA 구현체의 연결을 노출할 수 있는 구성에서 같은 `DataSource`의 JDBC 접근도 지원한다. `JdbcTemplate`은 `DataSourceUtils`를 통해 Spring이 연결한 자원을 사용한다. MyBatis-Spring을 함께 사용한다면 매퍼 팩터리와 트랜잭션 관리에 사용하는 `DataSource`를 맞춘다. [Spring Framework 6.2 API · JpaTransactionManager](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/orm/jpa/JpaTransactionManager.html) · [Spring Framework 6.2 · JDBC 연결 관리](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/connections.html) · [MyBatis-Spring · 트랜잭션](https://mybatis.org/spring/transactions.html)

1. 바깥 서비스에서 쓰기 작업의 트랜잭션 경계를 시작한다.
2. JPA 엔티티를 수정한 뒤 같은 작업에서 JDBC 조회가 수정 내용을 읽어야 하면 `EntityManager.flush()`를 호출한다.
3. JDBC가 관리 중인 엔티티의 행을 갱신하면 이미 로드한 객체에는 이전 값이 남을 수 있다. 보존할 변경을 플러시한 후 필요한 엔티티를 `refresh()`하거나, 영속성 컨텍스트를 비우고 다시 조회한다.
4. 통합 테스트에서 한쪽 작업을 실패시켜 같은 경계에 포함된 변경이 모두 롤백되는지 확인한다.

플러시는 SQL 실행을 앞당긴다. 최종 커밋은 같은 트랜잭션의 종료 시점에 이루어진다. 여러 데이터 소스가 각각 트랜잭션을 열면 자원별 커밋 범위를 따로 확인한다. [Jakarta Persistence 3.1 · 플러시, refresh, clear](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Spring Framework 6.2 · JPA와 트랜잭션](https://docs.spring.io/spring-framework/reference/6.2/data-access/orm/jpa.html)
