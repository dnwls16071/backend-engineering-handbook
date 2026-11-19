# Cost-Based Optimization and Histograms

비용 기반 옵티마이저는 후보 계획마다 읽을 페이지와 처리할 행 수 등을 추정한다. 행 수를 크게 잘못 추정하면 인덱스 선택과 조인 순서에도 영향을 줄 수 있다. 한 열의 값이 균등하게 분포하지 않을 때 히스토그램은 조건을 통과할 비율을 추정하는 데 쓰인다. [The Optimizer Cost Model](https://dev.mysql.com/doc/refman/8.4/en/cost-model.html) · [Optimizer Statistics](https://dev.mysql.com/doc/refman/8.4/en/optimizer-statistics.html)

## 1. 인덱스 통계와 열 히스토그램

MySQL에서 일반 `ANALYZE TABLE`은 키 분포를 분석한다. 열 히스토그램은 `UPDATE HISTOGRAM`으로 지정해 생성하며, 특히 인덱스에 없는 열의 상수 비교 조건을 추정할 때 유용하다. 범위 옵티마이저가 행 수를 추정할 수 있으면 그 추정이 히스토그램보다 우선할 수 있다. 히스토그램은 열 단위이므로 두 조건의 값이 함께 나타나는 빈도까지 표현하지 않는다. [ANALYZE TABLE](https://dev.mysql.com/doc/refman/8.4/en/analyze-table.html) · [Optimizer Statistics](https://dev.mysql.com/doc/refman/8.4/en/optimizer-statistics.html)

## 2. 실습 · 자주 나오는 값과 드문 값

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다. `status`에 별도 인덱스가 없는 상태에서 비교한다.

```sql
SELECT status, COUNT(*) AS orders FROM perf5_orders GROUP BY status;

EXPLAIN ANALYZE FORMAT=TREE SELECT order_id FROM perf5_orders WHERE status = 'RETURNED';

ANALYZE TABLE perf5_orders UPDATE HISTOGRAM ON status WITH 16 BUCKETS;

SELECT JSON_PRETTY(HISTOGRAM)
FROM INFORMATION_SCHEMA.COLUMN_STATISTICS
WHERE SCHEMA_NAME = DATABASE()
  AND TABLE_NAME = 'perf5_orders' AND COLUMN_NAME = 'status';

EXPLAIN ANALYZE FORMAT=TREE SELECT order_id FROM perf5_orders WHERE status = 'RETURNED';
EXPLAIN ANALYZE FORMAT=TREE SELECT order_id FROM perf5_orders WHERE status = 'PAID';

ANALYZE TABLE perf5_orders DROP HISTOGRAM ON status;
```

스캔 방식이 같아도 필터의 예상 행 수는 달라질 수 있다. 필터가 예상한 행 수와 실제로 통과한 행 수 사이의 오차를 비교한다. 조인 계획에서는 이런 차이가 다음 단계로 이어지므로 각 입력과 조인 노드의 행 수를 함께 읽는다. [EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze)
