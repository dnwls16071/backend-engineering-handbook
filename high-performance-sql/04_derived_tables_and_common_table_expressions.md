# Derived Tables and Common Table Expressions

파생 테이블은 `FROM` 절에 놓인 서브쿼리의 결과다. CTE(Common Table Expression)는 `WITH` 절에서 중간 결과에 이름을 붙인다. PostgreSQL 18에서는 같은 결과를 표현하는 두 쿼리도 조건을 어디까지 밀어 넣을 수 있는지, 중간 결과를 여러 곳에서 재사용하는지에 따라 실행 계획이 달라질 수 있다.

## 1. 같은 집계를 파생 테이블과 CTE로 표현하기

같은 세션에서 아래 블록을 순서대로 실행한다. 고객 1,000명에게 주문을 10건씩 만들고, `customer_id`로 주문을 찾는 인덱스를 추가한다.

```sql
CREATE TEMP TABLE report_orders AS
SELECT n AS order_id, n % 1000 + 1 AS customer_id,
       CASE WHEN n <= 7500 THEN 'paid' ELSE 'pending' END AS status,
       n % 100 + 1 AS amount
FROM generate_series(1, 10000) AS g(n);
CREATE INDEX ON report_orders (customer_id);
ANALYZE report_orders;
```

```sql
-- FROM 절의 파생 테이블
SELECT totals.customer_id, totals.paid_total
FROM (
    SELECT customer_id, SUM(amount) AS paid_total
    FROM report_orders
    WHERE status = 'paid'
    GROUP BY customer_id
) AS totals
WHERE totals.customer_id = 42;

-- WITH 절의 CTE
WITH totals AS (
    SELECT customer_id, SUM(amount) AS paid_total
    FROM report_orders
    WHERE status = 'paid'
    GROUP BY customer_id
)
SELECT customer_id, paid_total
FROM totals
WHERE customer_id = 42;
```

두 쿼리 모두 고객 `42`의 결제 합계 `336`을 반환한다. 파생 테이블의 별칭 `totals`는 해당 `FROM` 항목을 가리킨다. CTE 이름은 같은 SQL 문에서 여러 번 참조할 수 있고, 비재귀 `WITH`에서는 뒤에 정의된 CTE도 앞선 CTE를 참조할 수 있다. [PostgreSQL 18 FROM 절의 서브쿼리](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-SUBQUERIES) · [PostgreSQL 18 WITH 절](https://www.postgresql.org/docs/18/queries-with.html)

## 2. 실행 계획에서 인라인 확장과 구체화 비교하기

단순한 `FROM` 서브쿼리는 플래너가 바깥 쿼리와 합칠 수 있다. 위 두 쿼리 앞에 `EXPLAIN (ANALYZE, BUFFERS)`를 붙이면 `GROUP BY`에 필요한 집계와 그룹 키 조건 `customer_id = 42`가 적용된 스캔을 확인할 수 있다.

| 비재귀이며 `VOLATILE` 함수가 없는 `SELECT` CTE | PostgreSQL 18 동작 |
| --- | --- |
| 한 번 참조 | 기본적으로 바깥 쿼리와 합쳐 최적화한다. |
| 여러 번 참조 | 기본적으로 별도로 계산한 중간 결과를 참조마다 읽는다. |
| `AS MATERIALIZED` | CTE를 별도로 계산한다. 여러 참조가 공유하는 계산을 한 번만 수행할 때 유용하다. |
| `AS NOT MATERIALIZED` | CTE를 바깥 쿼리에 합친다. 참조별 조건을 원본 스캔에 적용할 수 있지만, 공통 계산이 반복될 수 있다. |

`NOT MATERIALIZED`는 재귀 CTE나 부작용이 있는 CTE에 지정하면 무시된다. 아래는 고객 `42`와 `43`의 결제 주문 수를 각각 조회하는 쿼리다. `EXPLAIN` 줄을 빼면 각 고객의 주문 수 `8`이 반환된다. `AS NOT MATERIALIZED`를 `AS` 또는 `AS MATERIALIZED`로 바꿔 실행 계획을 비교한다. [PostgreSQL 18 CTE 구체화](https://www.postgresql.org/docs/18/queries-with.html#QUERIES-WITH-CTE-MATERIALIZATION) · [PostgreSQL 18 SELECT의 WITH 절](https://www.postgresql.org/docs/18/sql-select.html#SQL-WITH)

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH paid AS NOT MATERIALIZED (
    SELECT customer_id FROM report_orders WHERE status = 'paid'
)
SELECT 42 AS customer_id, COUNT(*) AS paid_orders
FROM paid WHERE customer_id = 42
UNION ALL
SELECT 43, COUNT(*)
FROM paid WHERE customer_id = 43;
```

구체화한 계획에서는 `CTE Scan`과 각 스캔에 적용된 `Filter`를 찾는다. 합쳐진 계획에서는 `report_orders` 스캔에 고객 조건이 적용되는지 확인한다. 스캔 방식은 데이터와 통계에 따라 달라지므로 실제 행 수, 버퍼 사용량, 반복 횟수까지 비교한다. [PostgreSQL 18 EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
