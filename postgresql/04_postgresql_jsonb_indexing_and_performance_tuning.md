# PostgreSQL JSONB, Indexing, and Performance Tuning

이 문서는 결제 이벤트 20만 건을 생성해 `jsonb` 조건과 계좌별 최신 조회를 예로 든다. 쿼리의 연산자와 정렬 순서에 맞춰 인덱스를 선택하고, 실행 계획과 운영 지표로 실제 효과를 판단한다. 실습 데이터는 앞 문서의 테이블과 별도로 만든다.

## 실습 데이터 만들기

```sql
CREATE TABLE payment_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id integer NOT NULL,
    occurred_at timestamptz NOT NULL,
    payload jsonb NOT NULL
);

INSERT INTO payment_events (account_id, occurred_at, payload)
SELECT n % 2000,
       TIMESTAMPTZ '2025-01-01 00:00:00+00' + n * INTERVAL '1 minute',
       jsonb_build_object(
           'type', CASE WHEN n % 97 = 0 THEN 'refund' ELSE 'payment' END,
           'source', CASE WHEN n % 2 = 0 THEN 'web' ELSE 'app' END
       )
FROM generate_series(1, 200000) AS sample(n);

ANALYZE payment_events;
```

## 1. JSONB와 GIN 역인덱스

`json`은 입력 텍스트를 저장하고 읽을 때 파싱한다. `jsonb`는 입력을 분해한 형식으로 저장하며 GIN 인덱스를 지원한다. 자주 필터링하거나 조인하는 계좌 ID와 시각은 일반 열로 두고, 이벤트 유형에 따라 달라지는 부가 값은 `payload`에 둘 수 있다.

| 표현 | 결과 |
| --- | --- |
| `payload -> 'type'` | `type` 값을 JSONB로 가져온다. |
| `payload ->> 'type'` | 값을 SQL 텍스트로 가져온다. |
| `payload ? 'source'` | 최상위 키 `source`의 존재 여부를 확인한다. |
| `payload @> '{"type":"refund"}'` | 문서가 지정한 JSON 구조를 포함하는지 확인한다. |

GIN은 문서에서 얻은 키나 값으로 행 후보를 찾는 역인덱스다. `jsonb_ops`는 기본 연산자 클래스이며 `?`, `@>`, `@?`, `@@` 등을 지원한다. `jsonb_path_ops`는 `@>`, `@?`, `@@`를 지원하고, `?`로 키 존재 여부를 확인하는 조회에는 적용되지 않는다. 포함 검색이 중심인 아래 예제에서는 `jsonb_path_ops`를 선택한다.

```sql
CREATE INDEX payment_events_payload_gin_idx
    ON payment_events USING GIN (payload jsonb_path_ops);

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM payment_events
WHERE payload @> '{"type":"refund"}'::jsonb;
```

PostgreSQL 18.4 실습에서는 GIN의 `Bitmap Index Scan`으로 후보를 찾고 `Bitmap Heap Scan`으로 테이블을 읽어 환불 이벤트 2,061건을 집계했다.

특정 JSON 필드를 텍스트로 꺼내 `payload ->> 'type' = 'refund'`로 자주 비교한다면 그 표현식을 대상으로 B-tree 인덱스를 검토한다. 쿼리에서 쓰는 표현식과 연산자가 인덱스의 지원 범위에 들어가는지 확인한다.

**공식 문서** [JSON 타입과 JSONB 인덱싱](https://www.postgresql.org/docs/current/datatype-json.html) · [JSON 함수와 연산자](https://www.postgresql.org/docs/current/functions-json.html) · [표현식 인덱스](https://www.postgresql.org/docs/current/indexes-expressional.html)

## 2. 조회 조건에 맞는 인덱스 고르기

인덱스는 필요한 행이나 순서를 찾는 비용을 줄일 수 있다. 인덱스마다 저장 공간과 쓰기 시 유지 비용이 생기므로, 반복해서 실행되는 쿼리의 필터와 정렬 순서를 먼저 확인한다.

| 유형 | 고려할 조회 |
| --- | --- |
| B-tree | 동등 비교, 범위, 정렬. 계좌 ID로 필터링한 뒤 최신 시각 순으로 조회하는 경우 |
| Hash | `=` 비교가 필요한 경우. B-tree도 동등 비교를 지원하므로 실행 계획을 비교한다. |
| GIN | JSONB 포함 검색, 배열 원소나 전문 검색 토큰을 기준으로 행을 찾는 경우 |
| GiST | 범위의 겹침, 기하 연산 등 해당 연산자 클래스가 지원하는 조회 |
| SP-GiST | 접두사나 공간 데이터처럼 분할 구조로 검색할 수 있는 조회 |
| BRIN | 시각처럼 값의 순서가 실제 페이지 저장 순서와 잘 맞는 대형 테이블의 범위 조회 |

복합 B-tree 인덱스는 `account_id = 42`처럼 앞 열을 동등 조건으로 고정하고, 뒤 열에 범위나 정렬을 적용하는 조회에 적합하다. 예를 들어 `(account_id, occurred_at DESC, id DESC)`는 계좌별 최신 목록의 조건과 정렬을 한 번에 지원한다.

**공식 문서** [PostgreSQL 인덱스 유형](https://www.postgresql.org/docs/current/indexes-types.html) · [다중 열 인덱스](https://www.postgresql.org/docs/current/indexes-multicolumn.html)

## 3. EXPLAIN으로 인덱스 전후 비교하기

아래 SQL은 계좌 `42`의 최신 거래 20건을 읽는 동일 쿼리를 복합 인덱스 생성 전후에 실행한다. 결과 행과 정렬은 같아야 하며, 비교 대상은 스캔 방식, 정렬 여부, 버퍼 접근과 실행 시간이다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, occurred_at, payload ->> 'type' AS event_type
FROM payment_events
WHERE account_id = 42
ORDER BY occurred_at DESC, id DESC
LIMIT 20;

CREATE INDEX payment_events_account_timeline_idx
    ON payment_events (account_id, occurred_at DESC, id DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, occurred_at, payload ->> 'type' AS event_type
FROM payment_events
WHERE account_id = 42
ORDER BY occurred_at DESC, id DESC
LIMIT 20;
```

PostgreSQL 18.4에서 두 쿼리 모두 같은 순서로 20행을 반환했다. 인덱스 생성 전에는 `Parallel Seq Scan`과 `Sort`가 있었고, 생성 후에는 복합 인덱스의 `Index Scan`으로 정렬된 행을 가져왔다. 실습에서 실행 계획 최상단의 공유 버퍼 접근도 `hit=1889 read=626`에서 `hit=20 read=3`으로 달라졌다. 이 값은 해당 데이터와 캐시 상태에서 관측한 결과다.

| 항목 | 읽는 방법 |
| --- | --- |
| `Seq Scan`, `Index Scan`, `Sort` | 행을 어디에서 찾아 어떤 순서로 반환하는지 본다. 인덱스가 정렬을 제공하면 별도의 `Sort`가 빠질 수 있다. |
| 예상 `rows`, 실제 `rows`, `loops` | 계획 당시 예상과 실행 결과를 비교한다. 반복되는 노드의 실제 행 수와 시간은 실행 1회당 평균으로 표시된다. |
| `Buffers: shared hit/read` | 공유 버퍼에서 찾은 블록과 공유 버퍼로 읽은 블록을 확인한다. `read` 값에는 OS 캐시에서 읽은 경우도 포함될 수 있다. |
| `Execution Time` | 캐시 상태와 동시 부하를 맞추고 여러 번 측정한다. |

`EXPLAIN ANALYZE`는 쿼리를 실제 실행한다. 변경 쿼리를 조사할 때는 부작용을 통제할 수 있는 환경에서 실행한다. 작은 테이블이나 대부분의 행을 읽는 조건에서는 순차 스캔이 더 저렴할 수 있다.

**공식 문서** [EXPLAIN 실행 계획 읽기](https://www.postgresql.org/docs/current/using-explain.html) · [EXPLAIN 명령](https://www.postgresql.org/docs/current/sql-explain.html)

## 4. 쿼리와 인덱스 최적화 전략

| 상황 | 검토할 방법 |
| --- | --- |
| 날짜별 조회에서 시각 열에 함수를 적용함 | 같은 업무 시간대의 시작·종료 시각을 구하고 `occurred_at >= start_at AND occurred_at < end_at` 범위로 비교한다. |
| 같은 표현식으로 반복 검색함 | `lower(email)`처럼 쿼리에서 사용하는 표현식을 인덱스에 정의할 수 있다. 값이 바뀔 때 인덱스를 다시 계산하는 비용도 살핀다. |
| 일부 상태의 행만 자주 조회함 | Partial Index로 해당 행만 인덱싱한다. 계획 시점에 쿼리 조건이 인덱스 조건을 포함한다고 판단할 수 있어야 한다. |
| 일부 열만 반환하는 반복 조회에서 테이블 접근이 많음 | `INCLUDE`로 반환 열을 인덱스에 추가하는 방식을 검토한다. Index-Only Scan의 효과는 힙 페이지의 가시성 상태에 따라 달라지므로 `Heap Fetches`도 확인한다. |

운영 중 인덱스를 추가할 때는 쓰기 영향도 고려한다. `CREATE INDEX CONCURRENTLY`는 인덱스를 만드는 동안 일반적인 쓰기를 허용하지만, 더 많은 작업과 대기 시간이 들 수 있으며 트랜잭션 블록 밖에서 실행해야 한다.

**공식 문서** [표현식 인덱스](https://www.postgresql.org/docs/current/indexes-expressional.html) · [부분 인덱스](https://www.postgresql.org/docs/current/indexes-partial.html) · [Index-Only Scan과 INCLUDE](https://www.postgresql.org/docs/current/indexes-index-only-scans.html) · [CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)

## 5. 운영 지표로 병목 좁히기

1. **비용이 큰 쿼리부터 고른다.** `pg_stat_statements`에서 누적 실행 시간, 호출 횟수, 평균 실행 시간을 함께 본다. 드물게 느린 쿼리와 짧지만 자주 실행되는 쿼리는 개선 기준이 다르다.
2. **실행 중 대기를 확인한다.** `pg_stat_activity`의 `state`, `wait_event_type`, `wait_event`를 보고 잠금이나 I/O 대기인지 좁힌다. 쿼리가 락을 기다리는 경우에는 이를 잡고 있는 트랜잭션부터 확인한다.
3. **테이블 상태와 통계를 확인한다.** 대량 변경 후 예상 행 수가 실제와 크게 다르면 `ANALYZE`와 자동 분석 상태를 확인한다. `VACUUM`은 불필요해진 행 버전의 공간을 재사용할 수 있게 하고, 가시성 맵도 갱신한다.
4. **변경 전후 부하를 맞춘다.** 같은 데이터 분포와 조회 조건에서 응답 시간, 처리량, 버퍼 접근, 쓰기 비용을 비교한다.

아래 운영 조회를 사용하려면 `shared_preload_libraries`에 `pg_stat_statements`를 추가하고 서버를 재시작한다. 이후 대상 데이터베이스에서 확장을 생성하고 통계를 조회한다.

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT queryid, calls, total_exec_time, mean_exec_time, rows, query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

**공식 문서** [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html) · [pg_stat_activity와 대기 이벤트](https://www.postgresql.org/docs/current/monitoring-stats.html) · [VACUUM과 통계 갱신](https://www.postgresql.org/docs/current/routine-vacuuming.html)
