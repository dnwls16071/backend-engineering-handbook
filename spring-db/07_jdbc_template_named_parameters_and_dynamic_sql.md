# JdbcTemplate Named Parameters and Dynamic SQL

## 1. 이름으로 SQL 값 바인딩하기

`JdbcTemplate`은 JDBC 자원 관리와 예외 변환을 담당한다. `NamedParameterJdbcTemplate`은 `:maxPrice`처럼 이름을 사용한 SQL을 JDBC 파라미터로 변환한다. SET과 WHERE 절에 값이 여러 개 들어갈 때 각 값의 역할이 이름으로 드러난다. `MapSqlParameterSource`에는 값과 필요할 경우 SQL 타입을 지정하고, JavaBean 프로퍼티를 그대로 사용할 때는 `BeanPropertySqlParameterSource`를 사용할 수 있다. [Spring Framework 6.2 · JDBC Core](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html)

## 2. 선택 조건에 맞춰 SQL 조립하기

[상품 테이블과 결과 레코드](06_data_access_architecture_and_repository_design.md)를 사용한다. 조건이 있을 때만 정해 둔 SQL 조각을 추가하고, 검색에 쓰는 값은 별도로 바인딩한다. 이 예제에서는 `%`와 `_`가 검색어에 포함되면 글자 그대로 검색한다. [Spring Framework 6.2 · NamedParameterJdbcTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html)

```java
import java.util.ArrayList;
import java.util.List;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;

public class JdbcCatalogSearch {

    private final NamedParameterJdbcTemplate jdbc;

    public JdbcCatalogSearch(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<CatalogItem> search(String keyword, Long maxPriceCents) {
        var conditions = new ArrayList<String>();
        var parameters = new MapSqlParameterSource();

        if (keyword != null && !keyword.isBlank()) {
            String literal = keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_");
            conditions.add("name LIKE :keyword ESCAPE '!'");
            parameters.addValue("keyword", "%" + literal + "%");
        }
        if (maxPriceCents != null) {
            conditions.add("price_cents <= :maxPrice");
            parameters.addValue("maxPrice", maxPriceCents);
        }

        String sql = "SELECT id, name, price_cents, stock FROM catalog_item";
        if (!conditions.isEmpty()) {
            sql += " WHERE " + String.join(" AND ", conditions);
        }

        return jdbc.query(sql + " ORDER BY id", parameters,
                (row, index) -> new CatalogItem(row.getLong("id"), row.getString("name"),
                        row.getLong("price_cents"), row.getInt("stock")));
    }
}
```

조건이 없으면 `WHERE` 절을 생략한다. 정렬 열을 입력으로 고를 때도 허용한 SQL 조각으로 매핑한다. 함수나 조인이 늘어나면서 문자열 조립이 복잡해지면 [MyBatis 동적 SQL](09_mybatis_sql_mapping_and_dynamic_queries.md) 또는 [Querydsl 조건식](12_querydsl_dynamic_jpa_queries.md)을 적용할 수 있다.

## 3. 등록 결과의 생성 키 읽기

`SimpleJdbcInsert`에는 `withTableName("catalog_item")`, `usingColumns("name", "price_cents", "stock")`, `usingGeneratedKeyColumns("id")`로 등록 대상을 선언할 수 있다. `executeAndReturnKey(...)`가 반환하는 `Number`에서 생성 키를 읽는다. SQL을 직접 작성하는 등록에서 키도 필요하면 `KeyHolder`를 받는 `update(...)` 오버로드를 사용할 수 있다. [Spring Framework 6.2 · SimpleJdbcInsert와 키 반환](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/simple.html) · [Spring Framework 6.2 · JDBC Core](https://docs.spring.io/spring-framework/reference/6.2/data-access/jdbc/core.html)
