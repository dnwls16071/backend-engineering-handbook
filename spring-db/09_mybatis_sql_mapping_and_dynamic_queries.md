# MyBatis SQL Mapping and Dynamic Queries

## 1. 매퍼 인터페이스와 XML 연결하기

MyBatis는 매퍼 메서드를 SQL 문에 연결하고 결과를 객체에 매핑한다. XML의 `namespace`를 매퍼 인터페이스의 전체 이름으로 지정하고, 문장의 `id`를 메서드 이름과 맞춘다. MyBatis-Spring Boot Starter에서는 `@Mapper`가 붙은 인터페이스를 스캔하거나 `@MapperScan`으로 범위를 지정할 수 있다. XML을 별도 경로에 두면 `mybatis.mapper-locations`로 등록한다. [MyBatis 3 · Mapper XML](https://mybatis.org/mybatis-3/sqlmap-xml.html) · [MyBatis Spring Boot Starter · 구성](https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/)

```java
package example.catalog;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface CatalogMapper {

    List<CatalogItem> search(@Param("namePattern") String namePattern,
                             @Param("maxPriceCents") Long maxPriceCents);
}
```

[상품 레코드](06_data_access_architecture_and_repository_design.md)를 같은 패키지에 두고 생성자에 대응하는 열과 타입을 지정한다. `namePattern`에는 호출자가 준비한 LIKE 패턴을 전달한다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "https://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="example.catalog.CatalogMapper">
  <resultMap id="catalogItem" type="example.catalog.CatalogItem">
    <constructor>
      <idArg column="id" javaType="_long"/>
      <arg column="name" javaType="string"/>
      <arg column="price_cents" javaType="_long"/>
      <arg column="stock" javaType="_int"/>
    </constructor>
  </resultMap>

  <select id="search" resultMap="catalogItem">
    SELECT id, name, price_cents, stock FROM catalog_item
    <where>
      <if test="namePattern != null">name LIKE #{namePattern}</if>
      <if test="maxPriceCents != null">AND price_cents &lt;= #{maxPriceCents}</if>
    </where>
    ORDER BY id
  </select>
</mapper>
```

## 2. 동적 SQL과 생성 키 처리

| 요소 | 동작 |
| --- | --- |
| `<if>` | 조건을 만족하는 경우에만 해당 SQL을 포함한다. |
| `<where>` | 조건이 생기면 `WHERE`를 추가하고 선행 `AND` 또는 `OR`를 제거한다. |
| `<set>` | SQL 수정 절을 추가하고 마지막 쉼표를 정리한다. |
| `<choose>` | 여러 후보에서 첫 번째 일치 조건이나 기본 분기를 적용한다. |
| `<foreach>` | 목록을 순회하며 `IN` 등의 바인딩 목록을 구성한다. |

`#{value}`는 JDBC 파라미터로 바인딩하고 `${value}`는 SQL 문자열에 값을 삽입한다. 사용자 검색 값에는 `#{...}`를 쓴다. 생성 키를 객체에 채우려면 JDBC 드라이버가 생성 키 조회를 지원하는 경우 `useGeneratedKeys="true"`와 `keyProperty`를 사용한다. 이 경우 키를 받을 객체에 값이 기록될 수 있어야 한다. [MyBatis 3 · 파라미터와 생성 키](https://mybatis.org/mybatis-3/sqlmap-xml.html) · [MyBatis 3 · Dynamic SQL](https://mybatis.org/mybatis-3/dynamic-sql.html)

MyBatis-Spring에서 매퍼를 사용하면 Spring이 `SqlSession`의 생명주기와 트랜잭션을 관리한다. 매니저와 `SqlSessionFactory`가 같은 `DataSource`를 사용하도록 설정한다. [MyBatis-Spring · 트랜잭션](https://mybatis.org/spring/transactions.html)
