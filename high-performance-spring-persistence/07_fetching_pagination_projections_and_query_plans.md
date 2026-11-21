# Fetching, Pagination, Projections, and Query Plans

예제는 Spring Data JPA 3.5, Hibernate ORM 6.6, PostgreSQL을 기준으로 한다. `PurchaseOrder`는 `id`, `tenantId`, `createdAt`, `total`, `customer`, `lines`를 가진 주문 엔티티다. 주문을 수정하는 경로와 조회·내보내기 경로는 필요한 행, 열, 연관관계부터 정한다.

## 1. JDBC fetch size로 결과를 나눠 받는다

`Statement#setFetchSize()`는 드라이버가 결과를 한 번에 얼마나 가져올지 정하는 힌트다. `setMaxResults()`나 SQL `LIMIT`은 결과 행 수를 제한한다. fetch size는 결과 행 수를 그대로 두고 전송 단위를 조정한다. Hibernate에서는 `hibernate.jdbc.fetch_size`나 Hibernate `Query#setFetchSize()`로 지정할 수 있다. [Hibernate 6.6 JDBC 설정](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/cfg/JdbcSettings.html) · [Hibernate 6.6 `Query`](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/query/Query.html)

pgJDBC의 커서 기반 읽기는 일반적인 경우 autocommit이 꺼진 트랜잭션, `TYPE_FORWARD_ONLY`, 양수 fetch size, 단일 SQL 문을 요구한다. 조건을 만족하지 않으면 드라이버가 결과 전체를 가져올 수 있다. 사용한 드라이버 기준으로 결과 건수, 왕복 횟수와 메모리 사용을 확인한다. [pgJDBC 커서 기반 결과 조회](https://jdbc.postgresql.org/documentation/query/#getting-results-based-on-a-cursor)

## 2. OFFSET과 키셋으로 주문 목록을 나눈다

`Pageable`의 OFFSET 방식은 페이지 번호로 이동하기 쉽다. `Page`는 전체 개수를 얻기 위한 별도 쿼리를 실행할 수 있다. 전체 개수가 필요 없으면 `Slice`나 `Window`를 검토한다. 큰 OFFSET은 앞에서 건너뛸 행까지 처리하므로 깊은 페이지가 느릴 수 있다. [Spring Data JPA 쿼리 메서드](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html) · [PostgreSQL LIMIT과 OFFSET](https://www.postgresql.org/docs/18/queries-limit.html)

키셋은 마지막으로 반환한 행의 정렬 값으로 다음 범위를 찾는다. `created_at`이 같아도 순서가 일정하도록 `id`를 더한다. 아래는 두 열이 `NOT NULL`이고 두 열을 내림차순으로 정렬하는 경우다.

```sql
CREATE INDEX ix_purchase_order_feed
    ON purchase_order (tenant_id, created_at DESC, id DESC);

-- 이전 페이지 마지막 행의 created_at과 id를 이용한 다음 페이지
SELECT id, created_at, total
FROM purchase_order
WHERE tenant_id = 42
  AND (created_at, id) < (TIMESTAMPTZ '2026-11-20 09:00:00+09', 120)
ORDER BY created_at DESC, id DESC
LIMIT 21;
```

20건 단위라면 21번째 행은 다음 페이지 유무 확인에 쓰고, 반환한 20번째 행으로 커서를 만든다. Spring Data JPA 3.5의 키셋 스크롤링에 프로젝션을 쓰면 정렬 속성도 반환해야 한다. 문자열 `@Query` 메서드에서는 스크롤링을 지원하지 않으므로 지원되는 쿼리 메서드나 명시적인 키셋 조건을 사용한다. 커서 재사용 시 필터와 정렬 조건을 일치시키고, 목록이 변경되어도 같은 시점의 결과가 필요한지 결정한다. [Spring Data JPA 3.5 스크롤링](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html#jpa.query-methods.scroll) · [Spring Data Commons 3.5 키셋 스크롤링](https://docs.spring.io/spring-data/commons/reference/3.5/repositories/scrolling.html) · [OFFSET and Keyset Pagination in PostgreSQL](../high-performance-sql/10_offset_and_keyset_pagination_in_postgresql.md)

## 3. 조회 모델에 필요한 열과 계층을 만든다

엔티티를 변경할 필요가 없는 주문 요약은 DTO로 조회할 수 있다. JPQL의 생성자 표현식에 DTO의 패키지 이름과 생성자 인자 타입을 맞춘다. Spring Data JPA의 닫힌 인터페이스 프로젝션은 접근자에 대응하는 속성이 정해져 조회를 최적화할 수 있다. 중첩 속성이나 열린 프로젝션을 쓰면 선택된 열과 조인이 달라질 수 있어 SQL을 확인한다. [Spring Data JPA 3.5 프로젝션](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/projections.html)

```java
package com.example.order;

import java.math.BigDecimal;
import java.time.Instant;

public record OrderSummary(Long id, Instant createdAt, BigDecimal total) {}
```

```jpql
SELECT new com.example.order.OrderSummary(o.id, o.createdAt, o.total)
FROM PurchaseOrder o
WHERE o.tenantId = :tenantId
ORDER BY o.createdAt DESC, o.id DESC
```

일대다 DTO는 주문 ID와 품목 ID가 들어 있는 평탄한 행을 받은 뒤 주문 ID로 묶는다. 외부 조인으로 품목이 없는 주문도 읽었다면 품목 ID가 `NULL`인 행은 빈 목록으로 표현한다. 부모가 여러 행에 반복되므로 부모 단위 페이징은 먼저 부모를 고른 뒤 품목을 조회한다. [Jakarta Persistence 3.1의 JPQL](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Spring Data JPA 3.5 프로젝션](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/projections.html)

카테고리처럼 깊이가 고정되지 않은 계층은 노드마다 지연 조회를 호출하면 왕복이 늘 수 있다. PostgreSQL에서는 재귀 CTE로 필요한 하위 트리를 한 번에 읽고, ID·부모 ID·정렬 키를 DTO로 받은 뒤 애플리케이션에서 트리를 구성할 수 있다. 순환과 탐색 깊이도 다룬다. [PostgreSQL 재귀 CTE](https://www.postgresql.org/docs/18/queries-with.html#QUERIES-WITH-RECURSIVE) · [Recursive CTEs and Hierarchical Queries](../high-performance-sql/05_recursive_ctes_and_hierarchical_queries.md)

## 4. 엔티티와 연관관계의 로딩 시점을 정한다

- 엔티티 조회는 영속성 컨텍스트가 식별자로 객체를 관리하므로 변경 후 커밋하는 작업에 알맞다. 조회 전용 화면에서는 필요한 열만 읽고 연관관계를 어떤 쿼리로 가져올지 정한다. [Hibernate 6.6 Fetching](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#fetching)
- Jakarta Persistence의 기본값은 `@ManyToOne`·`@OneToOne`이 `EAGER`, `@OneToMany`·`@ManyToMany`가 `LAZY`다. `EAGER`는 필요한 연관 객체가 로딩돼야 한다는 요구다. Hibernate가 JPQL 조회 뒤 별도 `SELECT`로 로딩할 수도 있으므로 SQL 수를 확인한다. [Jakarta Persistence 3.1 연관관계](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate 6.6 엔티티 조회의 로딩 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#fetching-strategies-dynamic)
- `LAZY`는 공급자에 대한 힌트다. 세션이 열린 동안 반복해서 컬렉션을 순회하면 N+1 조회가 발생할 수 있다. 필요한 조회에 한해 `JOIN FETCH`, `EntityGraph`, Hibernate 지연 로딩의 배치 조회를 검토한다. [Spring Data JPA 3.5 EntityGraph](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html#jpa.entity-graph) · [Hibernate 6.6 배치 조회](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#fetching-batch)
- 초기화되지 않은 프록시나 컬렉션을 세션 밖에서 접근하면 Hibernate의 `LazyInitializationException`이 발생할 수 있다. 서비스의 트랜잭션 안에서 사용 사례에 필요한 조회를 수행하고 응답 DTO를 만든다. [Hibernate 6.6 `LazyInitializationException`](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/LazyInitializationException.html)

## 5. 컬렉션 fetch join과 페이지네이션을 나눠 실행한다

주문과 품목을 fetch join하면 한 주문이 여러 결과 행에 반복된다. Hibernate 6.6은 컬렉션 fetch join에 페이지 범위를 함께 주면 DB에서 전체 후보를 읽어 메모리에서 범위를 적용할 수 있다. 테스트에서 `spring.jpa.properties.hibernate.query.fail_on_pagination_over_collection_fetch=true`로 이런 쿼리를 실패시켜 찾을 수 있다. [Hibernate 6.6 HQL의 제한과 오프셋](https://docs.hibernate.org/orm/6.6/querylanguage/html_single/#hql-limit-offset) · [Hibernate 6.6 조회 설정](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/cfg/QuerySettings.html)

1. 정렬과 페이지 조건을 적용해 부모 주문 ID만 구한다.
2. ID 목록이 비어 있으면 바로 끝낸다. 값이 있으면 그 주문만 연관관계와 함께 조회한다.
3. `IN` 조건이 첫 질의의 순서를 유지해 주지 않으므로 첫 ID 목록의 순서로 다시 배열한다.

첫 번째 JPQL 쿼리에만 `setMaxResults()`와 필요한 페이지 조건을 적용한다.

```jpql
SELECT o.id
FROM PurchaseOrder o
WHERE o.tenantId = :tenantId
ORDER BY o.createdAt DESC, o.id DESC
```

두 번째 JPQL 쿼리의 `pageIds`에는 첫 번째 조회의 ID 목록을 전달한다.

```jpql
SELECT o
FROM PurchaseOrder o
LEFT JOIN FETCH o.lines
WHERE o.tenantId = :tenantId AND o.id IN :pageIds
```

두 질의 사이에 삭제나 수정이 일어날 수 있다. 페이지 ID 조회와 연관 조회가 같은 스냅샷을 보아야 한다면, PostgreSQL에서는 하나의 `REPEATABLE READ` 트랜잭션에서 실행하는 방법을 검토한다. [PostgreSQL 트랜잭션 격리](https://www.postgresql.org/docs/18/transaction-iso.html)

## 6. 스트리밍과 페이지 처리를 작업 특성에 맞춘다

리포지토리 메서드가 `Stream<T>`를 반환하면 연결과 결과 세트를 사용하는 동안 트랜잭션을 열어 두고 try-with-resources로 닫는다. 스트림만으로 드라이버가 결과를 조금씩 가져온다고 가정할 수 없다. fetch size와 드라이버 동작을 함께 확인한다. 엔티티를 읽으면 영속성 컨텍스트가 객체를 계속 보유할 수 있으므로 큰 읽기 작업은 DTO 스트림을 고려한다. 읽기 구간을 짧게 끝내거나 중단 지점부터 재시작해야 한다면 키셋 페이지 단위로 처리한다. [Spring Data JPA 3.5 반환 타입](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/query-return-types-reference.html) · [pgJDBC 커서 기반 결과 조회](https://jdbc.postgresql.org/documentation/query/#getting-results-based-on-a-cursor)

## 7. Hibernate와 DB의 쿼리 계획 캐시를 구분한다

Hibernate의 쿼리 계획 캐시는 HQL·JPQL 해석과 실행에 필요한 정보를 재사용한다. JDBC 드라이버의 준비된 문장 캐시와 DB의 실행 계획 재사용은 각각 다른 계층이다. PostgreSQL의 준비된 문장은 매개변수에 특화된 계획과 일반 계획 중 하나를 사용할 수 있다. 조건 값은 바인딩해 쿼리 모양을 재사용하고, `IN` 목록 길이나 동적 조건에 따라 생성 SQL이 달라질 때는 각 계층의 캐시 적중과 실행 시간을 별도로 확인한다. [Hibernate 6.6 조회 계획 설정](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/cfg/QuerySettings.html) · [PostgreSQL `PREPARE`](https://www.postgresql.org/docs/18/sql-prepare.html) · [JDBC Batching and Statement Caching](06_jdbc_batching_and_statement_caching.md)
