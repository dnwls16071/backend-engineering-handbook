# Diagnosing and Tuning Full Table Scans

`EXPLAIN FORMAT=TRADITIONAL`에서 접근 유형 `ALL`은 전체 테이블 스캔, `index`는 전체 인덱스 스캔을 뜻한다. `range`는 인덱스에서 정해진 구간을 탐색한다. `possible_keys`는 탐색 후보, `key`는 실제로 선택한 인덱스, `rows`는 검사할 행 수의 추정치다. [MySQL EXPLAIN 출력](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)

## 전체 스캔이 선택되는 이유

- 테이블이 작거나 조건에 맞는 행이 많으면 전체를 읽는 편이 저렴할 수 있다. 예를 들어 주문 대부분이 `PAID`라면 상태 인덱스에서 각 주문의 원본 행을 다시 읽는 비용이 크다. 예상 행 수가 실제 분포와 크게 다르면 `ANALYZE TABLE`로 인덱스 통계를 갱신한 뒤 계획을 비교한다. [MySQL 전체 테이블 스캔](https://dev.mysql.com/doc/refman/8.4/en/table-scan-avoidance.html) · [MySQL ANALYZE TABLE](https://dev.mysql.com/doc/refman/8.4/en/analyze-table.html)
- 조건에 맞는 인덱스가 있는지 확인한다. 인덱스 컬럼을 `DATE()`로 감싸거나 `CAST()`로 타입을 바꾸면 일반 인덱스로 탐색할 구간을 만들기 어려울 수 있다. 문자열 컬럼을 숫자와 비교하는 암시적 변환도 문자열 인덱스를 통한 탐색을 막는다. 입력값 타입을 컬럼과 맞추고, 함수가 필요한 조건은 범위 조건이나 함수 기반 인덱스를 검토한다. [MySQL 범위 최적화](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [MySQL 표현식 타입 변환](https://dev.mysql.com/doc/refman/8.4/en/type-conversion.html) · [Generated Columns and Functional Indexes](32_generated_columns_and_functional_indexes.md)

## 날짜 조건 전후의 실제 읽기 비교

[Composite Indexes and Access Types](01_composite_indexes_and_access_types.md)의 `mysql_lab_dispatches` 실습 데이터에서 `DATETIME` 컬럼을 비교한다. 두 쿼리는 같은 날짜에 출고한 행을 반환하며, `notes`를 조회하므로 시각 인덱스만으로 결과를 만들 수 없다.

```sql
CREATE INDEX ix_dispatches_time_demo ON mysql_lab_dispatches (dispatched_at);

EXPLAIN ANALYZE FORMAT=TREE
SELECT dispatch_id, notes
FROM mysql_lab_dispatches
WHERE DATE(dispatched_at) = '2025-02-01';

EXPLAIN ANALYZE FORMAT=TREE
SELECT dispatch_id, notes
FROM mysql_lab_dispatches
WHERE dispatched_at >= '2025-02-01'
  AND dispatched_at < '2025-02-02';

DROP INDEX ix_dispatches_time_demo ON mysql_lab_dispatches;
```

`EXPLAIN ANALYZE`는 쿼리를 실행한다. 이 데이터에서는 두 조건 모두 24행에 해당한다. 두 계획의 테이블 스캔 또는 인덱스 범위 스캔 단계에서 예상치와 실제 `rows`, `loops`, 실행 시간을 대조하면 같은 결과를 얻기 위해 읽는 범위가 달라졌는지 확인할 수 있다. [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze) · [Tuning Full Table Scans with Composite Indexes](../database-performance/04_tuning_full_table_scans_with_composite_indexes.md)
