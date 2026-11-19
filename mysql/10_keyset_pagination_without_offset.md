# Keyset Pagination Without OFFSET

깊은 페이지의 `OFFSET`은 앞에서 건너뛸 행도 처리해야 한다. 키셋 페이징은 직전 페이지의 마지막 정렬 키를 경계로 전달해 다음 구간을 탐색한다. 정렬 열의 값이 겹칠 수 있으면 기본 키처럼 유일한 열을 포함해 안정적인 순서를 만든다. [LIMIT Query Optimization](https://dev.mysql.com/doc/refman/8.4/en/limit-optimization.html) · [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html)

## 실습 · 출고 시각과 출고 번호로 다음 페이지 찾기

실습 환경은 MySQL 8.4(InnoDB)다. [01번의 출고 테이블](01_composite_indexes_and_access_types.md)을 사용한다. 커서의 두 값은 직전 페이지 마지막 행의 시각과 출고 번호다. 다음 예시는 공통 데이터에 있는 임의의 경계 행에서 이어 읽는다.

```sql
CREATE INDEX idx_dispatch_page ON mysql_lab_dispatches
    (hub_id, dispatched_at DESC, dispatch_id DESC);

SET @cursor_at = '2025-01-30 05:00:00';
SET @cursor_id = 701;

EXPLAIN ANALYZE FORMAT=TREE
SELECT dispatch_id, dispatched_at
FROM mysql_lab_dispatches
WHERE hub_id = 2
  AND (dispatched_at < @cursor_at
       OR (dispatched_at = @cursor_at AND dispatch_id < @cursor_id))
ORDER BY dispatched_at DESC, dispatch_id DESC
LIMIT 20;

DROP INDEX idx_dispatch_page ON mysql_lab_dispatches;
```

내림차순에서는 경계보다 작은 키를 읽는다. 시각이 같으면 출고 번호를 비교해 경계 행을 제외하고 뒤따르는 행을 찾는다. MySQL에서는 복합 키에 행 생성자 비교를 쓰는 경우와 위처럼 분해하는 경우의 범위 활용이 다를 수 있으므로 계획의 실제 범위를 비교할 수 있다. [Row Constructor Expression Optimization](https://dev.mysql.com/doc/refman/8.4/en/row-constructor-optimization.html)

다음 페이지를 읽을 때 같은 필터와 정렬을 유지한다. 커서는 순회 위치를 나타내며, 동시 삽입이나 정렬 키 변경이 보이는 방식은 트랜잭션의 읽기 시점에 따라 달라진다. OFFSET과 커서 방식의 비교는 [Sorting, Pagination, and Grouping Optimization](../database-performance/13_sorting_pagination_and_grouping_optimization.md)에 이어진다.
