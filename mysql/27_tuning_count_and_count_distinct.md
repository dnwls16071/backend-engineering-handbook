# Tuning COUNT and COUNT DISTINCT

## 먼저 집계 의미를 확인한다

| 표현 | 집계 대상 |
| --- | --- |
| `COUNT(*)` | 쿼리 결과의 모든 행 |
| `COUNT(user_id)` | `user_id`가 `NULL`이 아닌 행 |
| `COUNT(DISTINCT user_id)` | `NULL`을 제외한 서로 다른 사용자 ID |
| `COUNT(DISTINCT tenant_id, user_id)` | 두 값이 모두 `NULL`이 아닌 서로 다른 값의 조합 |

InnoDB는 트랜잭션마다 보이는 행이 다를 수 있어 정확한 행 수를 하나의 값으로 보관하지 않는다. 조건 없는 단순 집계에서는 일반적으로 작은 보조 인덱스를 순회하고, 보조 인덱스가 없다면 클러스터형 인덱스를 사용한다. `COUNT(*)`를 `COUNT(1)`로 바꿔도 이 처리 방식은 같다. [MySQL 집계 함수](https://dev.mysql.com/doc/refman/8.4/en/aggregate-functions.html)

## 조건과 인덱스를 맞춘다

`visit_events`에 `(tenant_id, visited_at)`과 `(tenant_id, user_id)` 인덱스가 있다고 가정한다.

```sql
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM visit_events
WHERE tenant_id = 42
  AND visited_at >= '2026-11-01';

EXPLAIN ANALYZE
SELECT COUNT(DISTINCT tenant_id, user_id)
FROM visit_events;
```

첫 쿼리는 테넌트와 날짜 조건이 읽는 범위를 좁히는지 본다. 두 번째 쿼리는 인덱스의 선두 열 조합을 사용하는 단일 테이블 집계로, 조건이 맞으면 Loose Index Scan 후보가 된다. 계획에서 실제 읽은 행과 중복 제거 작업을 비교해 효과를 확인한다. `EXPLAIN ANALYZE`는 실제 실행하므로 대표 데이터가 있는 검증 환경에서 비교한다. [MySQL 그룹 집계 최적화](https://dev.mysql.com/doc/refman/8.4/en/group-by-optimization.html) · [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html)

같은 집계를 자주 반복한다면 정확도와 최신성 요구를 먼저 정한다. 갱신 때 정확한 보조 카운터를 함께 바꾸는 방법은 빨리 읽을 수 있지만, 같은 카운터 행에 쓰기가 집중될 수 있다. 캐시나 주기 집계는 집계 시각을 함께 제공한다. [MySQL COUNT 최적화와 카운터 테이블](https://dev.mysql.com/doc/refman/8.4/en/aggregate-functions.html)
