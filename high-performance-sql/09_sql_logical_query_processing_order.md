# SQL Logical Query Processing Order

## 1. 행을 만든 뒤 필터링하고 집계한다

PostgreSQL 18에서 각 절의 입력을 추적하면 행이 어디서 사라지는지 확인하기 쉽다. 일반적인 쿼리 블록은 다음 순서로 결과의 의미를 정한다. [PostgreSQL `SELECT`](https://www.postgresql.org/docs/18/sql-select.html) · [PostgreSQL 테이블 표현식](https://www.postgresql.org/docs/18/queries-table-expressions.html)

| 단계 | 영향을 받는 대상 |
| --- | --- |
| `FROM`, `JOIN`, `ON` | 조인 후보의 일치 여부와 외부 조인이 보존할 행 |
| `WHERE` | 집계에 들어가는 개별 행 |
| `GROUP BY`와 일반 집계 | 같은 그룹 키를 가진 입력 행 |
| `HAVING` | 집계 이후 유지할 그룹 |
| 윈도 함수와 `SELECT` | 남은 행이나 그룹에 계산을 적용하고 출력 열 구성 |
| `DISTINCT`, 집합 연산 | 결과 열 기준 중복 제거 또는 쿼리 결과 결합 |
| 최종 `ORDER BY`, `OFFSET`, `LIMIT` | 출력 순서, 건너뛸 행과 반환할 행 수 |

실행 계획에서는 결과를 보존하는 범위에서 필터를 스캔 아래로 내려 보내거나 조인 순서를 바꿀 수 있다. 계산식이 정렬이나 중복 제거에 필요하지 않으면 PostgreSQL이 일부 출력식의 평가를 `LIMIT` 뒤로 미룰 수도 있다. 실제 연산과 읽기 비용은 실행 계획에서 확인한다. [PostgreSQL `SELECT`의 출력식 평가](https://www.postgresql.org/docs/18/sql-select.html#SQL-SELECT-LIST) · [PostgreSQL 실행 계획](https://www.postgresql.org/docs/18/using-explain.html)

## 2. 그룹을 거른 뒤 윈도 함수를 적용한다

```sql
WITH orders(customer_id, status, amount) AS (
    VALUES (1, 'PAID', 70), (1, 'PAID', 50), (1, 'NEW', 500),
           (2, 'PAID', 35), (3, 'PAID', 120)
)
SELECT customer_id, SUM(amount) AS paid_total,
       RANK() OVER (ORDER BY SUM(amount) DESC) AS paid_rank,
       SUM(SUM(amount)) OVER () AS qualifying_total
FROM orders
WHERE status = 'PAID'
GROUP BY customer_id
HAVING SUM(amount) >= 100
ORDER BY paid_rank, customer_id;
```

고객 1과 3만 남고 각 합계는 120, 순위는 1, 두 고객 합계는 240이다. `WHERE`가 미결제 행을 먼저 제외하고, `HAVING`이 고객 2의 그룹을 제외한다. 윈도 함수의 결과를 필터링하려면 이 쿼리를 CTE나 파생 테이블로 감싼 뒤 외부 `WHERE`에서 `paid_rank`를 사용한다. PostgreSQL에서 같은 쿼리 블록의 `WHERE`와 `HAVING`에는 원본 열이나 집계식을 쓰고, `paid_rank` 같은 출력 별칭은 외부 쿼리에서 참조한다. [PostgreSQL 윈도 함수 평가 범위](https://www.postgresql.org/docs/18/tutorial-window.html) · [PostgreSQL 별칭과 `SELECT` 목록](https://www.postgresql.org/docs/18/sql-select.html#SQL-SELECT-LIST)

## 3. 집합 연산 이후 전체 결과를 정렬한다

```sql
SELECT order_id FROM (VALUES (1), (3)) AS current_orders(order_id)
UNION
SELECT order_id FROM (VALUES (2), (3)) AS archived_orders(order_id)
ORDER BY order_id
LIMIT 1 OFFSET 1;
```

`UNION`으로 중복된 `3`을 제거하고 전체 ID를 오름차순으로 정렬하므로 `2`를 반환한다. 각 입력 쿼리에 별도로 `ORDER BY`와 `LIMIT`을 적용하려면 그 입력을 괄호로 묶는다. 합쳐진 결과에서 정렬 표현식을 새로 계산하려면 집합 연산을 파생 테이블로 감싼다. [PostgreSQL 집합 연산](https://www.postgresql.org/docs/18/queries-union.html) · [PostgreSQL 최종 정렬 규칙](https://www.postgresql.org/docs/18/queries-order.html)
