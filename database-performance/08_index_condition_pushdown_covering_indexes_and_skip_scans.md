# Index Condition Pushdown, Covering Indexes, and Skip Scans

인덱스 최적화는 어떤 범위를 읽는지, 원본 행을 언제 조회하는지, 인덱스만으로 결과를 만들 수 있는지를 나눠 보면 이해하기 쉽다.

| 기법 | 줄이는 작업 | MySQL EXPLAIN에서 확인할 값 |
| --- | --- | --- |
| Index Condition Pushdown(ICP) | 인덱스에 있는 조건을 먼저 검사해 탈락한 후보의 원본 행 조회를 줄인다. | `Using index condition` |
| 커버링 인덱스 | 쿼리에 필요한 열이 인덱스에 있어 결과를 얻기 위한 원본 행 조회를 줄인다. | `Using index` |
| Skip Scan | 제약이 없는 선행 키의 고유 값별로 후행 키의 범위를 읽어 전체 인덱스 스캔을 피할 수 있다. | `Using index for skip scan` |

InnoDB의 ICP는 원본 행을 읽어야 하는 세컨더리 인덱스 접근에 적용된다. MySQL의 Skip Scan은 인덱스가 쿼리에 필요한 열을 제공하는 단일 테이블 조회 등 적용 요건이 있으며, 선행 키의 고유 값이 많으면 반복 탐색 비용도 커진다. [Index Condition Pushdown](https://dev.mysql.com/doc/refman/8.4/en/index-condition-pushdown-optimization.html) · [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)

## 실습 · 같은 인덱스에서 접근 방식 비교

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다.

```sql
CREATE INDEX perf5_access_path ON perf5_orders (status, ordered_at, total_amount);
ANALYZE TABLE perf5_orders;

EXPLAIN FORMAT=TRADITIONAL
SELECT order_id, note
FROM perf5_orders
WHERE status = 'PAID' AND ordered_at >= '2025-01-05' AND total_amount < 50;

EXPLAIN FORMAT=TRADITIONAL
SELECT order_id, ordered_at, total_amount
FROM perf5_orders
WHERE status = 'PAID' AND ordered_at >= '2025-01-05' AND total_amount < 50;

EXPLAIN FORMAT=TRADITIONAL
SELECT status, ordered_at
FROM perf5_orders
WHERE ordered_at >= '2025-01-07 22:00:00';

DROP INDEX perf5_access_path ON perf5_orders;
```

첫 쿼리는 `total_amount` 조건을 인덱스에서 확인하고도 `note`를 위해 원본 행이 필요하다. 두 번째는 반환 열까지 인덱스가 제공한다. 세 번째는 선행 열 `status`를 제한하지 않아 Skip Scan 후보가 된다. 어떤 접근이 실제로 선택되는지는 데이터 분포와 비용에 따라 달라진다.
