# PostgreSQL Index Design and Partition Pruning

PostgreSQL 18에서 조회 조건과 데이터 분포에 맞춰 인덱스를 선택한다. 다음 테이블에는 시간순으로 생성된 이벤트 20,000건이 들어 있다. 각 절의 인덱스는 다른 조회에 대응한다. 인덱스 선택 여부는 `EXPLAIN`으로 확인한다.

```sql
CREATE TABLE pg_index_demo (
    id bigint PRIMARY KEY,
    tenant_id integer NOT NULL,
    status text NOT NULL,
    actor_email text NOT NULL,
    occurred_at timestamptz NOT NULL,
    payload jsonb NOT NULL
);

INSERT INTO pg_index_demo
SELECT g, g % 97,
       CASE WHEN g % 100 = 0 THEN 'READY' ELSE 'DONE' END,
       'User-' || g || '@example.invalid',
       TIMESTAMPTZ '2025-01-01 00:00:00+00' + g * interval '1 minute',
       jsonb_build_object('kind', CASE WHEN g % 100 = 0 THEN 'review' ELSE 'done' END)
FROM generate_series(1, 20000) AS s(g);

ANALYZE pg_index_demo;
```

## 1. 부분 인덱스로 필요한 행만 인덱싱하기

작업 큐가 대부분 완료 상태이고 대기 행만 반복해서 읽는다면 READY 행만 인덱싱할 수 있다. 플래너는 질의의 WHERE가 인덱스 조건을 만족함을 계획 시점에 확인해야 한다. 예를 들어 모든 상태값에 재사용할 generic plan의 `status = $1`만으로는 아래 인덱스 조건을 증명할 수 없다. [PostgreSQL 부분 인덱스](https://www.postgresql.org/docs/18/indexes-partial.html)

```sql
CREATE INDEX pg_index_demo_ready_idx ON pg_index_demo (occurred_at, id)
WHERE status = 'READY';

EXPLAIN SELECT id FROM pg_index_demo WHERE status = 'READY'
ORDER BY occurred_at, id LIMIT 10;
```

## 2. 표현식 인덱스로 LOWER(email) 검색하기

대소문자를 무시하도록 설계한 이메일 검색 키는 `lower(actor_email)` 표현식으로 인덱싱할 수 있다. 조회에도 같은 표현식을 사용한다. 인덱스에 쓰는 함수는 불변이어야 하고, 쓰기 시 표현식을 계산하고 유지하는 비용이 든다. 고유 인덱스로 전환하려면 적용할 콜레이션에서 기존 데이터가 중복되는지 먼저 확인한다. [PostgreSQL 표현식 인덱스](https://www.postgresql.org/docs/18/indexes-expressional.html) · [CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

```sql
CREATE INDEX pg_index_demo_email_idx ON pg_index_demo (lower(actor_email));

SELECT id FROM pg_index_demo
WHERE lower(actor_email) = 'user-1200@example.invalid';
```

## 3. 복합 키와 INCLUDE 설계하기

B-tree의 키 열은 탐색과 정렬에 쓰인다. `INCLUDE` 열은 커버링 조회에 필요한 값을 담지만 해당 인덱스의 탐색 키와 유일성 판단에 참여하지 않는다. 예제에서는 테넌트를 고정한 뒤 시간과 ID로 정렬한다. Index Only Scan이 선택되더라도 visibility map이 설정되지 않은 페이지에서는 힙을 확인할 수 있다. 반환 열이 넓을수록 인덱스 크기와 쓰기 비용도 함께 측정한다. [PostgreSQL 복합 인덱스](https://www.postgresql.org/docs/18/indexes-multicolumn.html) · [Index Only Scan과 INCLUDE](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)

```sql
CREATE INDEX pg_index_demo_tenant_time_idx
    ON pg_index_demo (tenant_id, occurred_at DESC, id DESC) INCLUDE (status);

EXPLAIN SELECT id, occurred_at, status
FROM pg_index_demo WHERE tenant_id = 42
ORDER BY occurred_at DESC, id DESC LIMIT 10;
```

## 4. JSONB 검색과 GIN 연산자 클래스

기본 `jsonb_ops`는 포함 검색과 키 존재 검색을 지원한다. `jsonb_path_ops`는 `@>`, `@?`, `@@`를 지원하며 키 존재 연산자 `?`에는 사용할 수 없다. 아래 예제는 포함 검색 `@>`를 사용한다. 특정 속성을 문자열로 추출해 등호 검색만 한다면 해당 표현식의 B-tree도 비교한다. [PostgreSQL JSONB 인덱싱](https://www.postgresql.org/docs/18/datatype-json.html#JSON-INDEXING) · [JSONB 인덱스 실습](04_postgresql_jsonb_indexing_and_performance_tuning.md)

```sql
CREATE INDEX pg_index_demo_payload_idx
    ON pg_index_demo USING gin (payload jsonb_path_ops);

SELECT count(*) FROM pg_index_demo WHERE payload @> '{"kind":"review"}'::jsonb;
```

## 5. 시간순 대용량 로그를 위한 BRIN

BRIN은 힙 블록 범위의 요약을 저장한다. 저장 순서와 시간 컬럼이 강하게 연관된 이벤트 데이터에서 범위를 빠르게 제외할 수 있다. 후보 블록에서는 실제 행에 조건을 다시 적용한다. `pages_per_range`를 줄이면 범위 요약이 더 정밀해질 수 있지만 요약 항목 수가 늘어난다. 시간 순서가 섞인 적재 데이터에서는 실제 계획과 다시 검사한 행 수를 본다. [PostgreSQL BRIN](https://www.postgresql.org/docs/18/brin.html)

```sql
CREATE INDEX pg_index_demo_brin_idx ON pg_index_demo
    USING brin (occurred_at) WITH (pages_per_range = 32);

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM pg_index_demo
WHERE occurred_at >= TIMESTAMPTZ '2025-01-05 00:00:00+00'
  AND occurred_at <  TIMESTAMPTZ '2025-01-05 01:00:00+00';
```

## 6. 선언적 파티셔닝과 파티션 제외

시간 범위 파티션은 월별 보존 정책과 범위 조회를 함께 관리할 수 있다. PostgreSQL은 질의 조건과 파티션 경계로 불필요한 파티션을 제외한다. 파티션이 제외된 뒤 남은 파티션에서 어떤 접근 경로를 쓸지는 별도로 선택한다. 아래 조회의 계획에서 1월 파티션만 접근하는지 확인한다. 부모 테이블의 PRIMARY KEY나 UNIQUE 제약에는 모든 파티션 키 열을 포함해야 한다. [PostgreSQL 선언적 파티셔닝과 pruning](https://www.postgresql.org/docs/18/ddl-partitioning.html)

```sql
CREATE TABLE pg_event_partition_demo (
    id bigint NOT NULL,
    occurred_at timestamptz NOT NULL,
    PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE pg_event_partition_demo_jan PARTITION OF pg_event_partition_demo
    FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-02-01 00:00:00+00');
CREATE TABLE pg_event_partition_demo_feb PARTITION OF pg_event_partition_demo
    FOR VALUES FROM ('2025-02-01 00:00:00+00') TO ('2025-03-01 00:00:00+00');

EXPLAIN SELECT id FROM pg_event_partition_demo
WHERE occurred_at >= TIMESTAMPTZ '2025-01-10 00:00:00+00'
  AND occurred_at <  TIMESTAMPTZ '2025-01-11 00:00:00+00';
```

## 7. CREATE INDEX CONCURRENTLY로 쓰기 중 인덱스 생성하기

동시 인덱스 생성은 일반 쓰기를 허용하지만 여러 스캔을 수행하고 기존 트랜잭션이나 스냅샷을 기다릴 수 있다. 독립 문장으로 실행하며 진행 상태는 `pg_stat_progress_create_index`에서 확인한다. 실패하면 INVALID 인덱스가 남을 수 있으므로 카탈로그에서 상태를 확인하고 다시 생성하는 절차를 정한다. 파티션 부모에 `CONCURRENTLY`를 직접 사용할 수 없으므로 파티션별로 생성한 인덱스를 부모 인덱스에 연결할 수 있다. [PostgreSQL CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html) · [CREATE INDEX 진행 상태](https://www.postgresql.org/docs/18/progress-reporting.html) · [파티션 인덱스 연결](https://www.postgresql.org/docs/18/ddl-partitioning.html)

```sql
CREATE INDEX CONCURRENTLY pg_index_demo_status_idx ON pg_index_demo (status);
```
