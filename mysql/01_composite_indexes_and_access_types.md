# Composite Indexes and Access Types

복합 인덱스는 여러 열을 하나의 정렬된 키로 저장한다. `(hub_id, status, dispatched_at)` 인덱스는 허브별로 묶이고, 각 허브 안에서 상태와 출고 시각 순서로 정렬된다. 이 순서는 인덱스 정의에 의해 정해지므로 `WHERE` 절에서 조건을 나열하는 순서를 바꿔도 그대로다. [Multiple-Column Indexes](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html)

## 조건이 접근 범위를 만드는 방식

| 조회 조건 | 인덱스에서 찾는 범위 |
| --- | --- |
| `hub_id = 2` | 허브 2에 해당하는 연속 구간 |
| `hub_id = 2 AND status = 'SENT'` | 허브 2의 `SENT` 키 구간 |
| 앞 두 열이 동등 조건이고 `dispatched_at >= ...` | 해당 허브와 상태 안에서 지정 시각 이후의 구간 |
| `hub_id BETWEEN 2 AND 5 AND status = 'SENT'` | 일반적인 복합 범위 접근에서는 허브 범위를 읽으며 상태를 추가로 검사한다. |
| `status = 'SENT'` | 허브별로 해당 상태가 흩어진다. 요건과 비용에 따라 Skip Scan 등을 고려할 수 있다. |

`EXPLAIN`에서 비유일 키의 동등 조회는 `ref`, 구간 읽기는 `range`로 나타날 수 있다. `index`는 인덱스 전체 스캔이다. `key`에 인덱스 이름이 있는 경우에도 `type`, `key_len`, 예상 행 수를 같이 확인하면 탐색 범위를 구분할 수 있다. [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)

## 실습 · 접근 유형 비교

실습 환경은 MySQL 8.4(InnoDB)다. 아래 테이블은 02·03번 문서에서도 사용한다. 계획 선택은 데이터의 크기와 분포에 따라 달라진다.

```sql
CREATE TABLE mysql_lab_dispatches (
    dispatch_id BIGINT PRIMARY KEY,
    hub_id INT NOT NULL,
    status VARCHAR(12) NOT NULL,
    dispatched_at DATETIME NOT NULL,
    notes VARCHAR(255) NOT NULL,
    INDEX idx_hub_status_time (hub_id, status, dispatched_at)
) ENGINE = InnoDB;

INSERT INTO mysql_lab_dispatches (dispatch_id, hub_id, status, dispatched_at, notes)
WITH RECURSIVE digit(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM digit WHERE n < 9
),
ids AS (
    SELECT 1 + a.n + 10 * b.n + 100 * c.n AS id
    FROM digit a CROSS JOIN digit b CROSS JOIN digit c
)
SELECT id, 1 + MOD(id, 20),
       IF(MOD(id DIV 20, 4) = 0, 'RETRY', 'SENT'),
       TIMESTAMPADD(HOUR, id, '2025-01-01 00:00:00'), CONCAT('Dispatch ', id)
FROM ids;

ANALYZE TABLE mysql_lab_dispatches;

EXPLAIN FORMAT=TRADITIONAL
SELECT dispatch_id, dispatched_at
FROM mysql_lab_dispatches
WHERE hub_id = 2 AND status = 'SENT';

EXPLAIN FORMAT=TRADITIONAL
SELECT dispatch_id, dispatched_at
FROM mysql_lab_dispatches
WHERE hub_id = 2 AND status = 'SENT' AND dispatched_at >= '2025-02-10';
```

두 계획의 `type`과 `key_len`을 비교한다. 복합 인덱스로 스캔 범위를 줄이는 실습은 [Tuning Full Table Scans with Composite Indexes](../database-performance/04_tuning_full_table_scans_with_composite_indexes.md)에 있다.
