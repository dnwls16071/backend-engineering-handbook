# LATERAL Derived Tables for Top-N Queries

`LATERAL`을 붙인 파생 테이블은 같은 `FROM` 절에서 앞에 나온 테이블의 열을 사용할 수 있다. 고객별 최근 주문처럼 바깥 행마다 조회 범위와 건수를 정해야 할 때 적합하다. [MySQL LATERAL 파생 테이블](https://dev.mysql.com/doc/refman/8.4/en/lateral-derived-tables.html)

## 고객마다 최근 두 건 조회

```sql
SELECT c.customer_id, recent.order_id, recent.created_at
FROM customers AS c
LEFT JOIN LATERAL (
    SELECT o.order_id, o.created_at
    FROM orders AS o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.created_at DESC, o.order_id DESC
    LIMIT 2
) AS recent ON TRUE
WHERE c.customer_id BETWEEN 1 AND 100
ORDER BY c.customer_id, recent.created_at DESC, recent.order_id DESC;
```

주문이 없는 고객을 결과에 남기려면 `LEFT JOIN`을 쓴다. 그 고객의 주문 열은 `NULL`이다. 파생 테이블 안의 `ORDER BY`는 고객별 두 건을 고르는 순서다. 최종 출력 순서는 바깥 `ORDER BY`에서 정한다. [MySQL LATERAL 조인 제약](https://dev.mysql.com/doc/refman/8.4/en/lateral-derived-tables.html) · [MySQL JOIN 문법](https://dev.mysql.com/doc/refman/8.4/en/join.html)

## 실행 계획 비교

`orders(customer_id, created_at, order_id)`를 인덱스 후보로 두고 `EXPLAIN ANALYZE`에서 바깥 고객 수, 안쪽 접근의 반복 횟수와 실제 행 수를 본다. 적은 고객마다 몇 건을 찾는 경우는 범위 탐색의 이점이 있다. 전체 고객을 한 번에 처리할 때는 `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC, order_id DESC)`로 랭킹한 후 거르는 계획과 비교한다. [MySQL 윈도 함수](https://dev.mysql.com/doc/refman/8.4/en/window-functions-usage.html) · [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
