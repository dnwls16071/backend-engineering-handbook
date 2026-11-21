# Prepared Statements, Execution Plans, and Caching

JDBC 문장 객체의 수명, 드라이버의 준비 정보, DB 세션의 실행 계획은 각각 관리된다. 반복 쿼리를 측정할 때 어느 계층이 재사용을 제공하는지 확인한다. [pgJDBC 서버 준비 문장](https://jdbc.postgresql.org/documentation/server-prepare/)

## 1. Statement 수명 주기와 실행 계획

`Connection.prepareStatement()`로 매개변수를 바인딩할 문장을 만들고, 값을 설정한 뒤 실행한다. 결과를 모두 소비하면 ResultSet과 Statement를 닫고 연결을 반환한다. `prepareStatement()` 호출과 서버에서 실행 계획을 준비하는 시점이 항상 일치하는 것은 아니다. PostgreSQL의 준비 문장은 파라미터 값으로 최적화하는 custom plan이나 여러 호출에서 공유하는 generic plan을 사용할 수 있다. 데이터 분포가 치우친 조건은 두 계획에서 비용이 달라질 수 있다. [PostgreSQL PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html)

```sql
PREPARE orders_by_customer (bigint) AS
    SELECT id, created_at
    FROM purchase_order
    WHERE customer_id = $1
    ORDER BY created_at DESC;

EXPLAIN (ANALYZE, BUFFERS) EXECUTE orders_by_customer(42);
DEALLOCATE orders_by_customer;
```

`purchase_order`가 있는 실습 DB의 같은 세션에서 실행한다. 대표 고객과 주문이 집중된 고객의 계획을 각각 비교한다. `ANALYZE`는 문장을 실제로 실행하므로 예시는 조회를 사용한다. [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html)

## 2. 문장 캐시와 실행 계획 캐시

| 계층 | 다시 사용하는 것 | 확인 방법 |
| --- | --- | --- |
| Hibernate | HQL·JPQL 해석 및 SQL 실행 준비에 쓰이는 내부 정보 | 쿼리 계획 캐시 hit/miss |
| pgJDBC | 물리 연결별로 관리하는 문장 관련 정보 | 드라이버 캐시 크기와 `prepareThreshold` |
| PostgreSQL | 서버 세션의 이름 있는 준비 문장 및 선택한 계획 | 같은 세션의 `pg_prepared_statements`, `EXPLAIN EXECUTE` |

pgJDBC의 기본 `prepareThreshold`는 5다. 드라이버는 SQL의 반복 실행 횟수와 설정에 따라 서버 측 준비 문장을 사용한다. JDBC Statement는 매번 정상적으로 종료하고 재사용은 드라이버에 맡긴다. SQL 텍스트와 파라미터 타입을 일관되게 유지하면 재사용 여부를 비교하기 쉽다. 풀의 물리 연결 수가 늘면 같은 총 실행량도 더 많은 세션에 분산된다. 각 계층의 캐시 적중과 DB의 계획 비용을 같은 것으로 해석하지 않는다. [pgJDBC 문장 캐시](https://jdbc.postgresql.org/documentation/server-prepare/) · [Hibernate Statistics](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/stat/Statistics.html) · [PostgreSQL pg_prepared_statements](https://www.postgresql.org/docs/17/view-pg-prepared-statements.html)
