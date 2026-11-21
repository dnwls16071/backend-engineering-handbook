# Writing Readable SQL Queries

SQL을 읽을 때 먼저 결과가 무엇을 한 행으로 표현하는지 확인할 수 있도록 작성한다. 이름과 별칭으로 테이블 역할을 표시하고, 조회 컬럼을 명시하며, 조인 관계와 조회 범위를 구분한다. 여러 단계로 계산할 때는 그 중간 결과의 의미를 설명하는 CTE 이름을 사용한다. [MySQL WITH 구문](https://dev.mysql.com/doc/refman/8.4/en/with.html)

## 행의 단위와 필터를 드러낸다

다음 쿼리는 테넌트의 11월 주문을 먼저 정의하고, 고객당 한 행으로 집계한다. 날짜 범위의 종료는 포함하지 않아 시각이나 소수 초 정밀도가 달라져도 월 경계가 분명하다.

```sql
WITH monthly_orders AS (
    SELECT customer_id, status
    FROM orders
    WHERE tenant_id = 42
      AND created_at >= '2026-11-01'
      AND created_at < '2026-12-01'
)
SELECT
    customer_id,
    COUNT(*) AS order_count,
    COUNT(CASE WHEN status = 'PAID' THEN 1 END) AS paid_order_count
FROM monthly_orders
GROUP BY customer_id
ORDER BY paid_order_count DESC, customer_id;
```

이 결과는 해당 기간에 주문한 고객만 포함한다. 주문이 없는 고객도 표시해야 한다면 `customers`를 기준으로 월 집계를 외부 조인한다. [LEFT JOIN Semantics and Optimization](34_left_join_semantics_and_optimization.md)

## 리팩터링 전후를 비교한다

- 조건에 `AND`와 `OR`가 섞이면 의도가 잘 드러나도록 괄호를 사용한다. 여러 테이블에 같은 이름의 열이 있으면 어느 열을 사용하는지 별칭으로 명시한다. [MySQL 연산자 우선순위](https://dev.mysql.com/doc/refman/8.4/en/operator-precedence.html)
- 가독성을 위해 CTE를 썼다면 MySQL이 이를 쿼리에 병합하거나 내부에서 구체화할 수 있다. 결과의 행 수, `NULL` 처리, 중복과 정렬을 먼저 비교한 뒤 실제 실행 계획에서 읽는 행과 반복을 확인한다. [MySQL 파생 테이블과 CTE 최적화](https://dev.mysql.com/doc/refman/8.4/en/derived-table-optimization.html) · [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
