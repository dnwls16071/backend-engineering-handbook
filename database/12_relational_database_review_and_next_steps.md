# Relational Database Review and Next Steps

관계형 데이터베이스를 다룰 때는 필요한 결과를 정확히 정의하고, 데이터 규칙을 강제하며, 실제 실행 계획으로 성능을 확인한다. 조인부터 저장 루틴까지 한 시나리오로 복습하고, 설계와 성능 최적화로 이어간다. 과정의 SQL 실습 환경은 MySQL 8.4다.

## 1. 한 시나리오로 복습하기

고객별 월간 주문 현황을 조회하고 주문 변경을 안전하게 처리하는 상황을 생각해 보자.

| 질문 | 관련 문서 |
| --- | --- |
| 주문이 없는 고객도 결과에 포함해야 하는가? | [INNER JOIN](01_inner_joins.md) · [OUTER, SELF, CROSS JOIN](02_outer_self_and_cross_joins.md) |
| 행을 결합할지, 다른 집합에 값이 존재하는지만 검사할지 결정했는가? | [Subqueries](03_subqueries.md) |
| 여러 출처의 결과를 합칠 때 중복을 유지해야 하는가? 상태별 건수와 금액은 어떻게 계산할까? | [UNION](04_union_and_union_all.md) · [CASE](05_case_expressions_and_conditional_aggregation.md) |
| 같은 조회 규칙을 여러 곳에서 재사용할 때 어떤 열과 행을 노출할까? | [Views](06_views.md) |
| 기간 필터와 정렬이 어떤 인덱스를 사용할 수 있는가? 실제 읽은 행은 몇 개인가? | [Index Fundamentals](07_b_tree_index_fundamentals.md) · [Composite and Covering Indexes](08_composite_and_covering_indexes.md) |
| 존재하지 않는 고객의 주문은 어떻게 막고, 주문과 상세의 변경을 어떻게 함께 처리할까? | [Constraints](09_data_integrity_and_constraints.md) · [Transactions](10_transactions_and_isolation_levels.md) |
| 호출자가 명시적으로 실행하는 로직과 변경 때마다 자동 실행되는 로직은 어디에 둘까? | [Stored Procedures, Functions, and Triggers](11_stored_procedures_functions_and_triggers.md) |

## 2. 설계와 성능 최적화로 이어가기

1. **데이터 모델링**은 고객, 주문, 주문 상세의 관계와 키를 먼저 정한다. 필수 속성, 유일성, 삭제 정책을 제약 조건으로 표현하고, 같은 사실을 여러 곳에 중복 저장해야 하는지 검토한다. [CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [Foreign Key Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)
2. **쿼리 최적화**는 느린 쿼리와 실제 데이터 분포를 기준으로 시작한다. MySQL 실습에서는 `EXPLAIN`으로 접근 경로와 예상 행 수를 확인하고, `EXPLAIN ANALYZE`로 실제 실행 행 수와 시간을 비교한다. 쿼리와 인덱스를 바꾼 후 같은 조건으로 다시 측정한다. [MySQL Optimization](https://dev.mysql.com/doc/refman/8.4/en/optimization.html) · [EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
3. **읽기 분산과 캐시**는 쿼리를 개선한 뒤 부하 특성에 따라 검토한다. 복제본으로 읽기를 분산하기 전에 복제 지연이 허용되는 조회를 골라야 한다. 외부 캐시를 적용할 때는 허용할 값의 최신성과 원본 변경 시 무효화 기준을 정한다. [MySQL Replication](https://dev.mysql.com/doc/refman/8.4/en/replication.html) · [캐시와 Redis Cluster](../cache/01_cache_fundamentals_and_redis_cluster.md)
