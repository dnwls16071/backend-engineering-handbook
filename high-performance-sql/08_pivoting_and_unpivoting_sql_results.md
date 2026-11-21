# Pivoting and Unpivoting SQL Results

피벗은 여러 행에 들어 있는 범주를 열로 옮긴다. 언피벗은 여러 열에 들어 있는 값을 범주와 값의 행으로 펼친다. 예제는 PostgreSQL 18 기준이다. 보고서에 필요한 범주가 고정되어 있으면 조건부 집계로 피벗을 만들 수 있다. [PostgreSQL 집계식과 `FILTER`](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-AGGREGATES)

## 1. 조건부 집계로 행을 열로 바꾼다

지역당 한 행을 만들고, 1월과 2월의 금액을 따로 합산한다.

```sql
WITH sales(region, sale_month, amount) AS (
    VALUES ('east', 1, 100), ('east', 1, 25),
           ('east', 2, NULL), ('west', 2, 80)
)
SELECT region,
       SUM(amount) FILTER (WHERE sale_month = 1) AS jan_sales,
       SUM(amount) FILTER (WHERE sale_month = 2) AS feb_sales,
       COUNT(*) FILTER (WHERE sale_month = 2) AS feb_rows
FROM sales
GROUP BY region
ORDER BY region;
```

| 지역 | 1월 합계 | 2월 합계 | 2월 입력 행 |
| --- | ---: | ---: | ---: |
| `east` | 125 | `NULL` | 1 |
| `west` | `NULL` | 80 | 1 |

`SUM` 결과만 보면 값이 모두 `NULL`인 경우와 해당 범주의 행이 없는 경우를 구분하기 어렵다. 구분해야 하면 범주의 `COUNT(*)`도 반환한다. 0을 표시할 때는 빈 결과와 미입력 값을 둘 다 0으로 처리할지 정하고 `COALESCE`를 사용한다. [PostgreSQL 집계 함수의 NULL 처리](https://www.postgresql.org/docs/18/functions-aggregate.html)

## 2. 열을 범주와 값의 행으로 펼친다

PostgreSQL에서는 `LATERAL`과 `VALUES`로 원본 한 행을 범주별 여러 행으로 펼칠 수 있다. 아래 쿼리는 금액이 `NULL`인 행도 유지한다.

```sql
WITH monthly(region, jan_sales, feb_sales) AS (
    VALUES ('east', 125, NULL), ('west', NULL, 80)
)
SELECT m.region, u.sale_month, u.amount
FROM monthly AS m
CROSS JOIN LATERAL (
    VALUES (1, m.jan_sales), (2, m.feb_sales)
) AS u(sale_month, amount)
ORDER BY m.region, u.sale_month;
```

SQL Server 2022의 `UNPIVOT` 연산자는 입력의 `NULL` 값에 해당하는 행을 결과에서 제거한다. 이 동작과 같은 결과가 필요하면 PostgreSQL 예제에 `WHERE u.amount IS NOT NULL`을 추가한다. 피벗이 여러 거래를 하나의 합계로 합쳤다면 언피벗으로 기존 거래 단위를 복원할 수 없다. [PostgreSQL `LATERAL`](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-LATERAL) · [SQL Server 2022의 `PIVOT`과 `UNPIVOT`](https://learn.microsoft.com/en-us/sql/t-sql/queries/from-using-pivot-and-unpivot?view=sql-server-ver16)
