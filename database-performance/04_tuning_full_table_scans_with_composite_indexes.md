# Tuning Full Table Scans with Composite Indexes

풀 테이블 스캔은 테이블의 넓은 부분을 반환하거나 테이블이 작을 때 합리적인 선택이다. 선별적인 조건에서 전체 스캔이 발생하면 인덱스가 있는지, 조건이 그 인덱스에서 연속적인 구간을 만들 수 있는지, 행을 추가로 찾아오는 비용이 얼마나 되는지 확인한다. [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [Multiple-Column Indexes](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html)

## 1. 인덱스 열 순서와 탐색 범위

`(status, ordered_at)`는 먼저 상태로 묶이고 그 안에서 시각순으로 정렬된다. 특정 상태를 동등 조건으로 고정하면 해당 상태의 시각 범위를 연속해서 읽을 수 있다. 시각만 범위로 지정하는 별도 조회는 상태 우선 인덱스와 궁합이 다르므로 그 조회의 빈도와 비용도 따로 확인한다.

## 2. 실습 · 운영 대시보드의 주문 검색

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다. 정확히 같은 조회를 인덱스 추가 전후로 실행한다.

```sql
EXPLAIN ANALYZE FORMAT=TREE
SELECT order_id, total_amount, note
FROM perf5_orders
WHERE status = 'RETURNED'
  AND ordered_at >= '2025-01-05' AND ordered_at < '2025-01-06';

CREATE INDEX perf5_scan_status_time ON perf5_orders (status, ordered_at);
ANALYZE TABLE perf5_orders;

EXPLAIN ANALYZE FORMAT=TREE
SELECT order_id, total_amount, note
FROM perf5_orders
WHERE status = 'RETURNED'
  AND ordered_at >= '2025-01-05' AND ordered_at < '2025-01-06';

DROP INDEX perf5_scan_status_time ON perf5_orders;
```

어떤 인덱스가 선택됐는지와 읽은 행 수가 얼마나 달라졌는지 확인한다. 조회가 인덱스에 없는 `note`를 요구하므로 범위에서 찾은 레코드의 원본 행도 조회해야 한다. 날짜 조건을 반개방 구간으로 쓰면 시각 열의 값을 함수로 감쌀 필요 없이 하루의 시작과 끝을 표현할 수 있다. 인덱스가 선택되지 않으면 실측 시간 한 번보다 데이터 분포와 통계, 반환 비중을 먼저 대조한다. [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) · [Clustered and Secondary Indexes](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)
