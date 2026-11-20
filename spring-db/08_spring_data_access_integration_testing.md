# Spring Data Access Integration Testing

## 1. 애플리케이션 실행 환경과 테스트 데이터베이스 분리하기

저장소 통합 테스트는 SQL 문법, 제약 조건, 생성 키, 결과 매핑까지 확인한다. 테스트 프로필에서 전용 JDBC URL을 사용하거나 임베디드 H2를 테스트마다 초기화한다. 운영 데이터베이스 고유의 SQL이나 잠금 동작에 의존한다면 같은 종류의 테스트 데이터베이스를 사용한다. 스키마와 테스트에 필요한 행은 `schema.sql`, `@Sql` 또는 마이그레이션 설정으로 준비할 수 있다. [Spring Boot 3.5 · 데이터베이스 초기화](https://docs.spring.io/spring-boot/3.5/how-to/data-initialization.html) · [Spring Boot 3.5 · 데이터 접근 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html) · [Spring Framework 6.2 · @Sql](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/executing-sql.html)

임베디드 데이터베이스는 별도 DB 서버 없이 테스트 프로세스에서 실행할 수 있다. `@JdbcTest`는 JDBC 테스트에 필요한 자동 설정을 제공하고, 테스트 트랜잭션은 기본적으로 종료 때 롤백된다. 애플리케이션이 설정한 데이터베이스를 그대로 사용하려면 교체 방식을 `@AutoConfigureTestDatabase(replace = NONE)`으로 명시할 수 있다. [Spring Boot 3.5 · JDBC 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html#testing.spring-boot-applications.autoconfigured-jdbc-tests)

## 2. 저장과 조회를 하나의 테스트에서 확인하기

[상품 테이블의 DDL](06_data_access_architecture_and_repository_design.md)을 테스트 리소스의 `schema.sql`에 두고 [JDBC 검색 구현](07_jdbc_template_named_parameters_and_dynamic_sql.md)을 가져온다. 테스트는 자신에게 필요한 행을 만든 뒤 결과를 확인한다.

```java
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.junit.jupiter.api.Assertions.assertEquals;

@JdbcTest
@Import(JdbcCatalogSearch.class)
class JdbcCatalogSearchTest {

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    JdbcCatalogSearch catalog;

    @Test
    void findsItemsWithinPriceLimit() {
        jdbc.update("INSERT INTO catalog_item (name, price_cents, stock) VALUES (?, ?, ?)",
                "Desk lamp", 2500, 8);

        assertEquals(List.of("Desk lamp"),
                catalog.search("lamp", 3000L).stream().map(CatalogItem::name).toList());
        assertEquals(List.of(), catalog.search("lamp", 1000L));
    }
}
```

## 3. 롤백이 미치는 범위 확인하기

테스트가 시작한 트랜잭션과 같은 스레드, 같은 매니저에 참여한 작업은 함께 롤백된다. 실제 HTTP 서버로 요청을 보내거나 애플리케이션이 `REQUIRES_NEW`에서 작업을 커밋하면 테스트 트랜잭션의 롤백 범위를 벗어날 수 있다. 그런 테스트는 별도 데이터베이스나 명시적 정리로 격리한다. [Spring Framework 6.2 · 테스트 관리 트랜잭션](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring Boot 3.5 · 웹 환경 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html)

실제 커밋 결과를 확인하려면 `TestTransaction.flagForCommit()`과 `TestTransaction.end()`로 테스트 중 커밋을 끝낸 뒤 새 트랜잭션에서 조회할 수 있다. JPA의 제약 조건이나 SQL 실행을 테스트할 때는 `flush()`로 데이터베이스에 변경을 보내고 검증한다. [Spring Framework 6.2 · TestTransaction과 수동 플러시](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
