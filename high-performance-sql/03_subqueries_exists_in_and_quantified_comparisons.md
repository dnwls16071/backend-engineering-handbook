# Subqueries, EXISTS, IN, and Quantified Comparisons

서브쿼리는 행의 존재 여부, 여러 값과의 비교, 단일 값 계산에 쓸 수 있다. 아래 예제는 PostgreSQL 18에서 같은 세션으로 순서대로 실행한다.

## 조인과 EXISTS의 결과 행 수

`JOIN`은 일치하는 두 행의 조합마다 결과를 만든다. `EXISTS`는 한 건 이상 일치하는지 확인하는 세미 조인의 의미를 가지므로, 일치하는 주문이 여러 건이어도 바깥의 고객 행을 한 번만 통과시킨다. 바깥 입력 자체에 중복이 있다면 그 중복은 그대로 유지된다. [PostgreSQL 18 EXISTS](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-EXISTS)

```sql
CREATE TEMP TABLE subquery_demo_customers (customer_id integer PRIMARY KEY);
CREATE TEMP TABLE subquery_demo_orders (
    order_id integer PRIMARY KEY,
    customer_id integer,
    created_at date NOT NULL
);
INSERT INTO subquery_demo_customers VALUES (1), (2);
INSERT INTO subquery_demo_orders VALUES
    (101, 1, DATE '2025-01-01'), (102, 1, DATE '2025-01-01'), (103, NULL, DATE '2025-01-02');

SELECT c.customer_id
FROM subquery_demo_customers AS c
JOIN subquery_demo_orders AS o ON o.customer_id = c.customer_id;

SELECT c.customer_id
FROM subquery_demo_customers AS c
WHERE EXISTS (SELECT 1 FROM subquery_demo_orders AS o WHERE o.customer_id = c.customer_id);
```

첫 쿼리는 고객 1을 두 번 반환한다. 두 번째 쿼리는 고객 1을 한 번 반환한다. `WHERE c.customer_id IN (SELECT customer_id FROM subquery_demo_orders)`도 이 예제에서는 고객 1만 남긴다. 고객 2의 `EXISTS`는 `FALSE`, `IN`은 `NULL`이며, `WHERE`는 둘 다 제외한다. [PostgreSQL 18 IN](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-IN)

## NOT EXISTS와 NOT IN의 NULL 처리

`NOT EXISTS`는 상관 조건을 만족하는 행이 없으면 참이다. `NOT IN`은 일치 값이 없더라도 오른쪽에 `NULL`이 있으면 비교 결과가 미정(`NULL`)이 된다. 아래 쿼리에서 고객 2의 두 열은 각각 `TRUE`, `NULL`이다. 두 식을 각각 `WHERE`에 넣으면 첫 번째는 고객 2를 남기고 두 번째는 0행을 반환한다. 두 입력의 비교 값이 모두 `NULL`이 될 수 없을 때는 이 동등 비교에서 같은 결과를 얻는다. [PostgreSQL 18 NOT IN](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-NOTIN)

```sql
SELECT c.customer_id,
       NOT EXISTS (SELECT 1 FROM subquery_demo_orders AS o
                   WHERE o.customer_id = c.customer_id) AS no_match,
       c.customer_id NOT IN (SELECT customer_id FROM subquery_demo_orders) AS absent
FROM subquery_demo_customers AS c
ORDER BY c.customer_id;
```

## ANY, SOME, ALL의 3값 논리

오른쪽 서브쿼리가 한 열을 반환할 때 `x = ANY (...)`는 `x IN (...)`, `x <> ALL (...)`은 `x NOT IN (...)`과 같다. `SOME`은 `ANY`와 같은 뜻이다. [PostgreSQL 18 ANY와 SOME](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-ANY-SOME) · [PostgreSQL 18 ALL](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-ALL)

| 식 | `TRUE` | `FALSE` | `NULL` |
| --- | --- | --- | --- |
| `x op ANY (...)` | 참인 비교가 하나 이상 | 모든 비교가 거짓이거나 0행 | 참은 없고 미정인 비교가 하나 이상 |
| `x op ALL (...)` | 모든 비교가 참이거나 0행 | 거짓인 비교가 하나 이상 | 거짓은 없고 미정인 비교가 하나 이상 |

```sql
SELECT 5 > ANY (VALUES (3), (NULL::integer)) AS any_true,
       5 > ALL (VALUES (3), (NULL::integer)) AS all_unknown,
       5 > ANY (SELECT 1 WHERE FALSE) AS any_empty,
       5 > ALL (SELECT 1 WHERE FALSE) AS all_empty;
```

## SELECT 목록의 스칼라 서브쿼리

스칼라 서브쿼리는 열 하나에서 값 하나를 돌려준다. 0행이면 `NULL`, 2행 이상이면 오류가 난다. 고객별 최신 주문 ID가 필요하면 한 행으로 제한하고, 같은 날짜의 주문끼리는 고유한 `order_id`로 우선순위를 정한다. [PostgreSQL 18 스칼라 서브쿼리](https://www.postgresql.org/docs/18/sql-expressions.html#SQL-SYNTAX-SCALAR-SUBQUERIES)

```sql
SELECT c.customer_id, (
    SELECT o.order_id
    FROM subquery_demo_orders AS o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.created_at DESC, o.order_id DESC
    LIMIT 1
) AS latest_order_id
FROM subquery_demo_customers AS c
ORDER BY c.customer_id;
```

고객 1의 최신 주문 ID는 `102`, 고객 2의 값은 `NULL`이다. 이 예제에서 `LIMIT 1`을 제거하면 고객 1에 주문이 두 건이므로 오류가 난다. 최신 시각에 해당하는 주문을 모두 반환하려면 해당 시각을 구한 뒤 그 값과 일치하는 주문 행을 조회한다.
