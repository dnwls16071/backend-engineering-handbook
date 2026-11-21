# OFFSET and Keyset Pagination in PostgreSQL

이 문서는 54~58번의 페이지네이션 주제를 페이지 번호, 커서, 역방향 조회와 동시 변경으로 정리한다. 예제는 PostgreSQL 18의 `posts` 테이블을 가정한다. `id`는 기본 키, `created_at`은 `timestamptz NOT NULL`이다. 테넌트별 게시물을 최근 순으로 보여 주므로 `(created_at, id)`로 정렬해 생성 시각이 같아도 순서를 확정한다. [PostgreSQL `LIMIT`과 `OFFSET`](https://www.postgresql.org/docs/18/queries-limit.html)

## 페이지 번호가 필요한 경우

```sql
SELECT id, created_at
FROM posts
WHERE tenant_id = 42
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 40;
```

페이지 크기가 20일 때 세 번째 페이지다. 서버는 건너뛸 행도 계산해야 하므로 깊은 페이지에서는 비용이 커질 수 있다. 조회 사이에 앞쪽 행이 삽입되거나 삭제되면 위치가 밀려 행을 중복해서 보거나 놓칠 수 있다. [PostgreSQL `LIMIT`과 `OFFSET`의 처리 비용](https://www.postgresql.org/docs/18/queries-limit.html) · [PostgreSQL `READ COMMITTED` 스냅샷](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

## 마지막 반환 행을 경계로 다음 페이지를 읽는다

```sql
CREATE INDEX ix_posts_tenant_feed
    ON posts (tenant_id, created_at DESC, id DESC);

-- 첫 페이지에서는 행 비교 조건을 생략한다.
SELECT id, created_at
FROM posts
WHERE tenant_id = 42
  AND (created_at, id) < (TIMESTAMPTZ '2026-11-20 09:00:00+09', 120)
ORDER BY created_at DESC, id DESC
LIMIT 21;
```

행 비교는 왼쪽 필드부터 진행한다. 경계와 `created_at`이 같은 행은 `id < 120`일 때 선택된다. 21번째 행이 있으면 다음 페이지가 있다는 신호로 쓰고, 응답은 20개로 자른다. 커서에는 추가로 읽은 21번째 행 대신 실제 반환한 20번째 행의 시각과 ID를 넣는다. `EXPLAIN (ANALYZE, BUFFERS)`로 인덱스 조건과 실제 읽은 행을 확인한다. [PostgreSQL 행 비교](https://www.postgresql.org/docs/18/functions-comparisons.html#ROW-WISE-COMPARISON) · [PostgreSQL 정렬 인덱스](https://www.postgresql.org/docs/18/indexes-ordering.html)

## 이전 페이지와 데이터 변경을 처리한다

- 이전 페이지는 현재 페이지의 첫 행을 경계로 `(created_at, id) > (...)`를 적용한다. 가까운 행부터 얻도록 두 정렬 키를 오름차순으로 바꾸고, 최대 20개를 선택한 다음 화면에 표시하기 전에 내림차순으로 뒤집는다. 같은 B-tree 인덱스는 역방향으로 읽을 수 있다. [PostgreSQL 정렬 인덱스](https://www.postgresql.org/docs/18/indexes-ordering.html)
- 커서를 만들 때 사용한 필터와 정렬 방식을 다음 요청에서도 유지한다. 커서를 인코딩할 때는 시각의 정밀도와 ID도 그대로 보존한다. 위 행 비교는 두 정렬 키의 방향이 같고 값이 `NULL`이 아닐 때의 예다. 정렬 방향이 섞이거나 `NULL`이 포함되면 각 정렬 항목의 순서와 `NULLS FIRST`·`LAST` 규칙을 반영해 조건을 작성한다. [PostgreSQL 행 비교](https://www.postgresql.org/docs/18/functions-comparisons.html#ROW-WISE-COMPARISON) · [PostgreSQL `ORDER BY`](https://www.postgresql.org/docs/18/queries-order.html)
- 커서는 이동 기준을 제공한다. 조회 사이에 행의 정렬 키나 조건 컬럼이 바뀌면 누락과 중복이 발생할 수 있다. 고정 시점의 내보내기가 필요하면 스냅샷을 유지한 읽기나 별도로 고정한 대상 집합을 고려한다. 페이지 수를 위한 정확한 전체 집계도 별도 비용이므로 다음 페이지 여부만 필요한 API는 한 건을 더 읽는 방식으로 충분하다. [PostgreSQL 반복 가능 읽기](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-REPEATABLE-READ) · [OFFSET and Keyset Pagination](../mysql/28_offset_and_keyset_pagination.md)
