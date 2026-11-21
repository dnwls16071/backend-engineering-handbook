# Spring Data JPA Foundations and Testing

이 장은 Spring Boot 3.5, Spring Data JPA 3.5, Hibernate ORM 6.6, Jakarta Persistence 3.1과 PostgreSQL을 기준으로 한다. 저장소 호출의 결과와 데이터베이스가 실제로 수행한 작업을 함께 확인한다. [Spring Boot 3.5 의존성 버전](https://docs.spring.io/spring-boot/3.5/appendix/dependency-versions/coordinates.html)

## 1. Spring Data JPA에서 데이터베이스까지

| 계층 | 역할 |
| --- | --- |
| Spring Data JPA | `JpaRepository`의 구현을 제공하고 메서드 이름이나 `@Query`로 저장소 쿼리를 정의할 수 있게 한다. |
| Jakarta Persistence(JPA) | `@Entity`, `EntityManager`, JPQL, 영속성 컨텍스트와 같은 ORM 계약을 정의한다. |
| Hibernate ORM | JPA 계약을 구현한다. 변경 감지와 플러시를 수행하고 데이터베이스 방언에 맞는 SQL을 생성한다. |
| JDBC 및 드라이버 | `PreparedStatement`의 파라미터를 바인딩하고 DB에서 SQL을 실행해 결과를 읽는다. |

예를 들어 `findByStatus`를 호출하면 Spring Data JPA가 저장소 메서드를 쿼리로 해석하고, Hibernate가 SQL로 변환해 PostgreSQL JDBC 드라이버로 실행한다. 반환 결과에 문제가 있으면 쿼리 의도, 생성 SQL과 바인딩 값, DB 실행 계획의 순서로 범위를 좁힌다. [Spring Data JPA 저장소](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa.html) · [Jakarta Persistence 3.1 명세](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate ORM 6.6 사용자 가이드](https://docs.hibernate.org/orm/6.6/userguide/html_single/)

## 2. 객체 모델과 관계형 모델의 차이

Java의 `order.getCustomer()`는 객체 참조를 탐색한다. 관계형 DB는 `orders.customer_id`의 값으로 관계를 표현하고, 고객 정보가 필요하면 조인하거나 별도의 조회를 실행한다. 지연 로딩된 고객을 주문 목록에서 한 건씩 접근하면 목록 조회 뒤 고객 조회가 반복되는 N+1 문제가 생길 수 있다. 조회 화면이 요구하는 데이터에 맞춰 fetch join이나 DTO 프로젝션을 선택하고 쿼리 수를 확인한다. [Hibernate 연관관계 페치 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)

객체 참조의 동일성과 DB 기본 키도 구분한다. 같은 영속성 컨텍스트에서는 동일한 엔티티 식별자가 하나의 관리 인스턴스를 가리킨다. `clear()`를 호출했거나 다른 영속성 컨텍스트에서 읽었다면 같은 행을 나타내는 객체가 별도로 만들어질 수 있다. 관리 중인 객체의 변경은 플러시 시점에 SQL로 반영되므로 객체를 수정한 시점과 DB에 쓰기가 발생한 시점도 달라질 수 있다. [Jakarta Persistence 3.1 영속성 컨텍스트](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate 플러시](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing)

## 3. 마이그레이션과 Hibernate 스키마 관리

Flyway나 Liquibase로 테이블, 인덱스, 제약 조건과 기존 데이터의 변환을 변경 이력으로 관리한다. Hibernate의 `validate`는 시작할 때 매핑에 필요한 테이블과 컬럼 타입 등의 호환성을 확인한다. 인덱스나 업무 제약의 적용 여부는 마이그레이션 테스트와 카탈로그 조회 등으로 확인한다. `none`은 Hibernate의 스키마 작업을 끄고, `create`와 `create-drop`은 초기화해도 되는 실습 DB에서 사용한다. `update`는 매핑에 따라 스키마 변경을 시도하므로 운영 배포의 변경 이력은 버전이 지정된 마이그레이션으로 남긴다. [Spring Boot 데이터베이스 초기화](https://docs.spring.io/spring-boot/3.5/how-to/data-initialization.html) · [Hibernate 스키마 관리 설정](https://docs.hibernate.org/orm/6.6/userguide/html_single/#configurations-hbmddl)

PostgreSQL에서 Flyway를 사용하려면 `org.flywaydb:flyway-core`와 `org.flywaydb:flyway-database-postgresql`을 추가한다. `src/main/resources/db/migration/V1__create_orders.sql`에 변경을 작성하고 다음 설정으로 Flyway에 스키마 변경을 맡긴다. [Spring Boot Flyway 설정](https://docs.spring.io/spring-boot/3.5/how-to/data-initialization.html#howto.data-initialization.migration-tool.flyway)

```properties
spring.flyway.enabled=true
spring.jpa.hibernate.ddl-auto=validate
spring.sql.init.mode=never
```

## 4. Hibernate 6의 SQL과 바인딩 로그

`spring.jpa.show-sql=true`는 Hibernate가 SQL을 표준 출력으로 보낸다. SQL을 애플리케이션의 로깅 설정으로 제어하려면 `org.hibernate.SQL`을 `DEBUG`로 켠다. 이 로거가 `where status=?`처럼 문장 구조를 기록하면 `org.hibernate.orm.jdbc.bind`의 `TRACE` 로그에서 파라미터 위치와 JDBC 타입, 값을 확인할 수 있다. `hibernate.format_sql`은 SQL 들여쓰기를 제어한다. [Hibernate 6 SQL 로깅](https://docs.hibernate.org/orm/6.6/introduction/html_single/#logging-sql)

```properties
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.orm.jdbc.bind=TRACE
```

바인딩 로그에는 개인정보와 토큰 같은 값이 기록될 수 있다. 위 설정은 합성 데이터를 사용하는 로컬·테스트 프로필에 두고 운영에서는 파라미터 로깅을 끈다. SQL 본문에 리터럴을 직접 넣는 쿼리도 값이 로그에 노출될 수 있으므로 파라미터로 전달한다.

## 5. 실제 DB에서 저장소 동작과 비용 테스트하기

`@DataJpaTest`는 엔티티와 JPA 저장소에 집중하는 테스트 슬라이스다. 테스트는 기본적으로 트랜잭션 안에서 실행되고 종료 시 롤백된다. PostgreSQL 방언, 제약, JSON 연산자를 확인하려면 운영과 같은 주요 버전의 별도 테스트 DB를 사용하고 동일한 마이그레이션을 적용한다. Testcontainers의 PostgreSQL 컨테이너에 `@ServiceConnection`을 붙이면 Spring Boot 3.5의 기본 `NON_TEST` 교체 정책이 자동 구성된 테스트 연결을 유지한다. 별도 데이터소스를 명시적으로 유지해야 하는 구성에서는 `@AutoConfigureTestDatabase(replace = Replace.NONE)`을 사용한다. [Spring Boot JPA 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html#testing.spring-boot-applications.autoconfigured-spring-data-jpa) · [Testcontainers 서비스 연결](https://docs.spring.io/spring-boot/3.5/reference/testing/testcontainers.html#testing.testcontainers.service-connections) · [데이터소스 교체 정책](https://docs.spring.io/spring-boot/3.5/api/java/org/springframework/boot/test/autoconfigure/jdbc/AutoConfigureTestDatabase.Replace.html)

- **저장과 조회**는 `save()` 후 `EntityManager.flush()`로 SQL을 실행하고, `clear()`로 1차 캐시를 비운 다음 다시 조회해 검증한다. DB에서 읽은 컬럼 값을 직접 검사할 필요가 있으면 같은 트랜잭션에서 JDBC로 조회한다. [Spring Framework 테스트 트랜잭션](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
- **커밋 시점 제약**은 예를 들어 PostgreSQL의 `DEFERRABLE INITIALLY DEFERRED` 외래 키로 확인한다. `TestTransaction.flagForCommit()`과 `TestTransaction.end()`로 테스트 트랜잭션을 커밋하고, 성공 경로에서 남는 데이터는 격리된 DB에서 정리한다. [Spring Framework의 `TestTransaction`](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html#testcontext-tx-programmatic-tx-mgt) · [PostgreSQL 지연 제약](https://www.postgresql.org/docs/17/sql-set-constraints.html)
- **조회 비용**은 테스트 데이터 준비 후 SQL 카운터를 초기화하고, 목록을 읽고 필요한 연관관계까지 접근한 뒤 쿼리 수를 단언한다. 실행 계획은 대표 데이터와 검색 조건으로 `EXPLAIN (ANALYZE, BUFFERS)`를 실행해 실제 처리 행 수와 버퍼 접근을 확인한다. `ANALYZE`가 쿼리를 실제 실행하므로 여기서는 조회 SQL에 적용한다. [Hibernate 통계](https://docs.hibernate.org/orm/6.6/userguide/html_single/#statistics) · [PostgreSQL `EXPLAIN`](https://www.postgresql.org/docs/17/sql-explain.html)
