# PostgreSQL Execution Plans and Query Diagnostics

PostgreSQL 18의 실행 계획에서 행 수 추정과 실제 처리량을 비교하고, 반복 실행되는 쿼리의 누적 비용을 확인한다. [PostgreSQL EXPLAIN 사용법](https://www.postgresql.org/docs/18/using-explain.html)

## 1. 실행 계획을 트리로 읽기

리프에서 테이블이나 인덱스의 접근 방식을 확인한다. 상위 노드는 입력을 필터링하거나 조인·정렬·집계해 결과를 만든다. `cost=a..b`는 시작 비용과 완료 비용의 추정값이며 밀리초와 직접 비교할 수 없다. `rows`와 `width`는 해당 노드가 출력할 행 수와 평균 행 폭의 추정치다. [PostgreSQL EXPLAIN의 추정값](https://www.postgresql.org/docs/18/using-explain.html)

## 2. EXPLAIN ANALYZE와 BUFFERS로 실제 비용 보기

`EXPLAIN (ANALYZE, BUFFERS)`는 문장을 실행해 실제 시간, 행 수, 반복 횟수와 버퍼 통계를 보여 준다. 반복 노드의 `actual rows`와 시간은 반복당 평균이므로 전체 반환량은 행 수에 `loops`를 곱해 해석한다. 상위 노드의 수치에 하위 작업이 포함될 수 있으므로 전체 트리의 시간을 단순 합산하지 않는다. `shared hit`는 공유 버퍼에서 찾은 블록이고, `shared read`는 공유 버퍼에 없어 읽어 들인 블록이다. 운영체제 캐시에서 공급됐을 수도 있다. 여기서는 부작용 없는 조회로 측정한다. [PostgreSQL EXPLAIN 옵션](https://www.postgresql.org/docs/18/sql-explain.html)

## 3. 통계 갱신이 필요한지 판단하기

갑자기 처리 행 수가 늘었다면 예상 행 수와 실제 행 수가 처음 크게 갈라지는 노드를 찾는다. 데이터 대량 적재나 분포 변경 이후에는 `pg_stat_user_tables`의 `last_analyze`, `last_autoanalyze`, `n_mod_since_analyze`를 참고한다. 통계가 낡았다면 `ANALYZE` 후 계획을 비교한다. 최신 통계에서도 특정 값의 편향이나 컬럼 간 상관관계가 추정에 반영되지 않을 수 있다. [PostgreSQL 플래너 통계](https://www.postgresql.org/docs/18/planner-stats.html)

## 4. 상관된 컬럼에 확장 통계 적용하기

아래 실습에서 `region_id`와 `zone_id`는 같은 값이다. 두 조건을 독립적으로 추정하면 함께 만족하는 행이 실제보다 적게 계산될 수 있다. 첫 계획과 확장 통계 적용 뒤의 계획에서 예상 행 수를 비교한다. 함수 종속성은 이 실습처럼 상수와의 등호 조건에 유용하고, `mcv`는 특정 값 조합의 빈도를 담는 데 쓴다. 확장 통계는 조회 결과를 바꾸지 않으며 테이블 조인의 선택도 추정에는 사용되지 않는다. [PostgreSQL 다변량 통계](https://www.postgresql.org/docs/18/multivariate-statistics-examples.html) · [CREATE STATISTICS](https://www.postgresql.org/docs/18/sql-createstatistics.html)

```sql
CREATE TABLE pg_plan_demo (
    id integer PRIMARY KEY,
    region_id integer NOT NULL,
    zone_id integer NOT NULL
);
INSERT INTO pg_plan_demo
SELECT g, g % 100, g % 100 FROM generate_series(1, 10000) AS s(g);
ANALYZE pg_plan_demo;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM pg_plan_demo WHERE region_id = 42 AND zone_id = 42;

CREATE STATISTICS pg_plan_region_zone (dependencies)
    ON region_id, zone_id FROM pg_plan_demo;
ANALYZE pg_plan_demo;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM pg_plan_demo WHERE region_id = 42 AND zone_id = 42;
```

## 5. Nested Loop, Hash Join, Merge Join 비교하기

| 방식 | 계획에서 확인할 부분 |
| --- | --- |
| Nested Loop | 외부 입력 행 수와 내부 접근의 `loops`를 본다. 작은 외부 입력과 인덱스로 빠르게 찾는 내부 입력에 적합할 수 있다. |
| Hash Join | 해시를 만드는 입력 크기와 `Batches`, 임시 I/O를 본다. 메모리에 맞지 않아 분할하는지도 확인한다. |
| Merge Join | 두 입력에 조인 키 순서가 어떻게 제공되는지 확인한다. Sort 노드가 있으면 정렬 비용도 포함한다. |

실제 입력 행 수와 반복, 메모리·I/O 비용을 비교한다. 앞 단계의 조건 추정이 빗나가면 다른 조인 방식을 선택해도 병목이 남을 수 있다. [PostgreSQL EXPLAIN의 조인 예제](https://www.postgresql.org/docs/18/using-explain.html)

## 6. 힙 구조와 Index Only Scan

PostgreSQL의 일반 테이블은 힙이고 인덱스는 별도로 저장된다. `CLUSTER`는 인덱스 순서로 테이블을 다시 쓰지만 이후 쓰기마다 그 순서를 유지하지 않는다. Index Only Scan이 가능하려면 필요한 값이 인덱스에 있어야 한다. 힙 페이지가 visibility map에서 all-visible로 표시되지 않으면 가시성 확인을 위해 힙을 읽을 수 있다. 계획의 `Heap Fetches`로 실제 힙 접근을 확인한다. [PostgreSQL CLUSTER](https://www.postgresql.org/docs/18/sql-cluster.html) · [Index Only Scan](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)

## 7. COUNT와 깊은 OFFSET의 비용

조건 없는 정확한 `COUNT(*)`는 MVCC 스냅샷에서 보이는 행을 세므로 테이블 또는 적합한 인덱스 전체를 읽는 비용이 든다. 깊은 `OFFSET`은 건너뛸 행도 서버에서 계산하게 한다. 다음 페이지가 목적이라면 고유한 정렬 키를 포함해 키셋 조건으로 범위를 좁힌다. 화면의 총 개수가 필요한지, 정확도와 새로고침 주기가 무엇인지 먼저 확인한다. [PostgreSQL 집계 함수](https://www.postgresql.org/docs/18/functions-aggregate.html) · [PostgreSQL LIMIT과 OFFSET](https://www.postgresql.org/docs/18/queries-limit.html) · [PostgreSQL 페이지네이션 실습](../high-performance-sql/10_offset_and_keyset_pagination_in_postgresql.md)

## 8. pg_stat_statements로 개선 대상 고르기

서버의 `shared_preload_libraries`에 `pg_stat_statements`를 추가하고 재시작한 뒤, 조회할 데이터베이스에서 `CREATE EXTENSION IF NOT EXISTS pg_stat_statements`를 실행한다. 기존 preload 목록은 유지한다. 누적 통계에서 `calls`, `total_exec_time`, `mean_exec_time`을 함께 보면 자주 호출돼 전체 부담이 큰 문장을 찾을 수 있다. 시간 단위는 밀리초다. `queryid`는 사용자·DB·최상위 문장 여부와 함께 사용하고, 버전을 가로지르는 영구 식별자로 가정하지 않는다. [PostgreSQL pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)

```sql
SELECT userid, queryid, toplevel, calls,
       round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 1) AS mean_ms,
       rows, shared_blks_read
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY total_exec_time DESC
LIMIT 10;
```
