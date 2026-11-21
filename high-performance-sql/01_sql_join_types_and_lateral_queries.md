# SQL Join Types and LATERAL Queries

조인 유형에 따라 일치하는 행의 조합, 보존되는 행, 결과의 행 수가 달라진다. 실습은 PostgreSQL 18에서 SQL 블록을 같은 세션으로 순서대로 실행한다.

```sql
CREATE TEMP TABLE join_demo_customers (customer_id integer PRIMARY KEY);
CREATE TEMP TABLE join_demo_orders (
    order_id integer PRIMARY KEY,
    customer_id integer NOT NULL,
    status text NOT NULL,
    created_at date NOT NULL
);
INSERT INTO join_demo_customers VALUES (1), (2), (3);
INSERT INTO join_demo_orders VALUES
    (101, 1, 'paid', DATE '2025-01-03'), (102, 1, 'paid', DATE '2025-01-03'),
    (103, 1, 'cancelled', DATE '2025-01-02'), (201, 2, 'cancelled', DATE '2025-01-01');
```

## CROSS JOIN, INNER JOIN, NATURAL JOIN

`CROSS JOIN`은 두 입력의 모든 조합을 만든다. 고객이 3명이고 주문이 4건이면 결과는 12행이다. 날짜와 상품을 교차 조인해 집계 표에 필요한 전체 조합을 만들 수도 있다. `INNER JOIN`은 `ON` 조건이 참인 조합만 반환한다. 아래에서는 고객 1에 대해 3행, 고객 2에 대해 1행이 나온다. [PostgreSQL 18 조인 유형](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)

```sql
SELECT COUNT(*) FROM join_demo_customers CROSS JOIN join_demo_orders;

SELECT c.customer_id, o.order_id
FROM join_demo_customers AS c
JOIN join_demo_orders AS o ON o.customer_id = c.customer_id;
```

`NATURAL JOIN`은 양쪽에 이름이 같은 모든 열을 조인 키로 삼는다. 위 테이블에서는 `customer_id`만 쓰지만 양쪽에 `status` 같은 열이 추가되면 기존 SQL의 매칭 조건도 바뀐다. 같은 이름의 열이 하나도 없으면 모든 조합을 반환한다. 키를 고정하려면 `USING (customer_id)`이나 `ON`으로 명시한다. [PostgreSQL 18의 NATURAL과 USING](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)

## LEFT JOIN과 FULL OUTER JOIN

모든 고객에게 결제 주문을 붙이려면 주문 상태를 `ON`에서 검사한다. 결제 주문이 없는 고객 2와 3은 주문 열이 `NULL`인 한 행씩을 얻는다. 같은 상태 조건을 `WHERE`로 옮기면 조인 결과에서 조건이 참인 결제 주문 행만 남아 두 고객 모두 빠진다. [PostgreSQL 18의 ON과 WHERE](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)

```sql
SELECT c.customer_id, o.order_id
FROM join_demo_customers AS c
LEFT JOIN join_demo_orders AS o
    ON o.customer_id = c.customer_id AND o.status = 'paid';

SELECT c.customer_id, o.order_id
FROM join_demo_customers AS c
LEFT JOIN join_demo_orders AS o ON o.customer_id = c.customer_id
WHERE o.status = 'paid';
```

`FULL OUTER JOIN`은 양쪽에서 매칭되지 않은 행도 보존하고, 반대쪽 열을 `NULL`로 채운다. 아래 예제는 키 1에서 `2 × 2 = 4`개의 매칭 행을 만들고, 왼쪽의 키 2와 오른쪽의 키 3을 한 행씩 더해 총 6행을 반환한다. 원본 키가 각각 어느 쪽에 있었는지 확인하려면 두 키를 따로 출력한다. [PostgreSQL 18 외부 조인](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)

```sql
SELECT a.k AS left_key, b.k AS right_key, a.label, b.label
FROM (VALUES (1, 'A1'), (1, 'A2'), (2, 'A3')) AS a(k, label)
FULL JOIN (VALUES (1, 'B1'), (1, 'B2'), (3, 'B3')) AS b(k, label) ON a.k = b.k;
```

## LATERAL로 고객마다 최근 두 건 조회

`LATERAL`을 붙인 `FROM` 서브쿼리는 앞에 나온 고객 행의 열을 참조할 수 있다. 이 예제는 고객별 최근 주문 두 건을 고른다. 날짜가 같으면 기본 키 `order_id`가 큰 주문을 먼저 선택한다. `LEFT JOIN LATERAL ... ON TRUE`는 주문이 없는 고객 3도 보존한다. `CROSS JOIN LATERAL`을 쓰면 해당 고객의 결과가 0행이다. [PostgreSQL 18 LATERAL 서브쿼리](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-LATERAL)

```sql
CREATE INDEX ON join_demo_orders (customer_id, created_at DESC, order_id DESC);

SELECT c.customer_id, recent.order_id, recent.created_at
FROM join_demo_customers AS c
LEFT JOIN LATERAL (
    SELECT o.order_id, o.created_at
    FROM join_demo_orders AS o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.created_at DESC, o.order_id DESC
    LIMIT 2
) AS recent ON TRUE
ORDER BY c.customer_id, recent.created_at DESC, recent.order_id DESC;
```

안쪽 `ORDER BY`는 고객별로 선택할 주문을 정하고 바깥 `ORDER BY`는 출력 순서를 정한다. 결과는 고객 1의 `102`, `101`, 고객 2의 `201`, 고객 3의 `NULL` 순이다. 복합 B-tree 인덱스를 사용하면 고객의 주문을 원하는 순서로 읽다가 두 건에서 멈출 수 있다. 많은 고객을 한 번에 조회할 때는 실행 계획에서 안쪽 탐색의 반복 횟수를 확인한다. [조인 실행 계획 읽기](02_join_algorithms_and_query_performance.md) · [PostgreSQL 18 인덱스와 정렬](https://www.postgresql.org/docs/18/indexes-ordering.html)
