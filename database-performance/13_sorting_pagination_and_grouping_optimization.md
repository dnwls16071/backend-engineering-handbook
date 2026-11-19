# Sorting, Pagination, and Grouping Optimization

인덱스에서 필요한 순서로 행을 읽을 수 있으면 정렬을 줄이고, 연속된 같은 키의 행을 묶어 집계할 수 있다. 페이징에서는 원하는 시작점부터 읽을 수 있는지가 중요하다.

## 1. 정렬과 페이징

| 방식 | 읽는 범위와 성질 |
| --- | --- |
| `ORDER BY` + `LIMIT` | 인덱스 순서가 맞으면 필요한 수의 행을 채웠을 때 읽기를 멈출 수 있다. 별도 정렬이 필요한 경우에는 후보를 읽어야 한다. |
| `LIMIT ... OFFSET` | 지정한 개수만큼 건너뛴 뒤 행을 반환한다. 깊은 페이지는 버릴 행도 처리해야 한다. |
| 지연 조인 | 인덱스에서 페이지에 필요한 키를 고른 뒤 본문 행을 가져온다. 건너뛰는 비용은 남지만 본문 조회를 줄일 수 있다. |
| 커서 기반 페이징 | 이전 페이지의 마지막 정렬 키 뒤에서 읽는다. 같은 시각의 행을 안정적으로 나누려면 유일한 보조 키까지 커서에 저장해야 한다. |

페이지 사이에 데이터가 바뀌면 조회 시점에 따라 결과도 달라질 수 있다. 커서는 조회 위치를 나타내며, 여러 요청 사이의 동일한 스냅샷을 보장하려면 별도의 일관성 설계가 필요하다. [ORDER BY Optimization](https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html) · [LIMIT Query Optimization](https://dev.mysql.com/doc/refman/8.4/en/limit-optimization.html) · [Derived Table Optimization](https://dev.mysql.com/doc/refman/8.4/en/derived-table-optimization.html)

## 2. 실습 · OFFSET과 커서 방식 비교

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다. 이 데이터에서 내림차순 5,000번째 주문은 `5001`이며 시각은 `2025-01-04 11:21:00`이다. 예제는 그 다음 행부터 가져오는 두 방법을 비교한다.

```sql
CREATE INDEX perf5_page_time ON perf5_orders (ordered_at DESC, order_id DESC);

EXPLAIN ANALYZE FORMAT=TREE
SELECT order_id, ordered_at
FROM perf5_orders
ORDER BY ordered_at DESC, order_id DESC
LIMIT 20 OFFSET 5000;

EXPLAIN ANALYZE FORMAT=TREE
SELECT order_id, ordered_at
FROM perf5_orders
WHERE ordered_at < '2025-01-04 11:21:00'
   OR (ordered_at = '2025-01-04 11:21:00' AND order_id < 5001)
ORDER BY ordered_at DESC, order_id DESC
LIMIT 20;

DROP INDEX perf5_page_time ON perf5_orders;
```

두 조회의 출력이 같은지 먼저 보고, 각 계획이 하위 연산자에서 읽은 행 수를 비교한다. 운영 코드에서는 하드코딩한 예제 값 대신 직전 페이지의 마지막 행에서 시각과 주문 번호를 얻는다.

## 3. GROUP BY와 인덱스 순서

- MySQL의 Loose Index Scan은 적용 조건을 만족할 때 그룹별로 일부 키만 읽는다. 예를 들어 `(customer_id, total_amount)` 인덱스에서 `GROUP BY customer_id`와 `MIN(total_amount)`를 처리할 수 있다. 전통 형식의 `EXPLAIN`에서는 `Using index for group-by`를 확인한다.
- Tight Index Scan은 해당 범위의 키를 읽으면서 인덱스 순서를 이용해 그룹을 처리할 수 있다. `SUM`처럼 그룹의 모든 값이 필요한 집계는 각 행의 값을 읽어야 한다.
- 정렬 또는 내부 임시 테이블을 사용하는 계획도 남을 수 있다. 특히 집계 결과인 `SUM(...)`을 기준으로 정렬하면 원본 키 순서만으로 결과 순서를 얻기 어렵다.

[GROUP BY Optimization](https://dev.mysql.com/doc/refman/8.4/en/group-by-optimization.html) · [Internal Temporary Table Use](https://dev.mysql.com/doc/refman/8.4/en/internal-temporary-tables.html)
