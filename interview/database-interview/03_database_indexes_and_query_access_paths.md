# Database Indexes and Query Access Paths

## 1. 인덱스란 무엇이고 어떤 장단점이 있나요?

**30–60초 답변**

> 인덱스는 키 값으로 필요한 행을 더 적은 페이지에서 찾도록 돕는 자료구조입니다. 조건에 맞는 행이 적을 때 전체 테이블을 훑는 비용을 줄일 수 있고, B-tree의 키 순서가 조회의 `ORDER BY`와 맞으면 별도 정렬도 생략할 수 있습니다. 유일 인덱스는 키의 중복을 막는 데도 쓰입니다. 인덱스는 저장 공간을 차지하고, `INSERT`나 `DELETE`, 인덱스 키를 바꾸는 `UPDATE`에서 인덱스도 유지해야 하므로 쓰기 비용이 증가합니다. 따라서 실제 조회의 조건과 정렬, 쓰기 빈도를 보고 추가합니다. [PostgreSQL 18의 인덱스 소개](https://www.postgresql.org/docs/18/indexes-intro.html) · [PostgreSQL 18의 인덱스와 `ORDER BY`](https://www.postgresql.org/docs/18/indexes-ordering.html) · [PostgreSQL 18의 유일 인덱스](https://www.postgresql.org/docs/18/indexes-unique.html)

**꼬리 질문 · `LIMIT`이 있는 조회에서 정렬에 맞춘 인덱스의 장점은 무엇인가요?**

`ORDER BY created_at DESC LIMIT 20`에서 인덱스가 필요한 순서로 행을 제공하면 앞의 20건을 찾은 시점에 읽기를 멈출 수 있습니다. 인덱스 순서를 사용할 수 없어 정렬한다면 상위 20건을 결정하기 위해 조건에 맞는 후보를 모두 살펴야 합니다. [PostgreSQL 18의 인덱스와 `ORDER BY`](https://www.postgresql.org/docs/18/indexes-ordering.html)

## 2. B-tree 인덱스와 해시 인덱스는 어떻게 다른가요?

**30–60초 답변**

> B-tree는 키를 정렬된 상태로 유지합니다. 루트부터 비교하면서 검색 시작 위치를 찾은 뒤 인접한 키를 읽을 수 있어 `=` 조회, `BETWEEN`이나 `<` 같은 범위 조회, 키 순서에 맞는 정렬에 활용할 수 있습니다. 해시 인덱스는 키의 해시값으로 버킷을 찾아 `=` 조회에 사용합니다. 해시값은 원래 키의 대소 관계를 보존하지 않으므로 키 범위나 정렬 순서를 제공할 수 없습니다. 실제 선택은 DB가 지원하는 인덱스 종류와 쿼리의 조건을 함께 봅니다. [PostgreSQL 18의 B-tree 및 해시 인덱스](https://www.postgresql.org/docs/18/indexes-types.html) · [MySQL 8.4의 B-tree와 해시 인덱스 비교](https://dev.mysql.com/doc/refman/8.4/en/index-btree-hash.html)

**꼬리 질문 · 동등 조건만 쓰면 해시 인덱스가 항상 더 빠른가요?**

B-tree도 동등 조건을 처리할 수 있습니다. 해시 인덱스는 데이터 분포에 따라 한 버킷에 항목이 몰리면 오버플로 페이지를 더 읽을 수 있습니다. 인덱스와 테이블 페이지의 접근 비용도 영향을 주므로, 실제 값 분포와 실행 계획을 확인해 판단합니다. [PostgreSQL 18의 해시 인덱스 개요](https://www.postgresql.org/docs/18/hash-index.html) · [PostgreSQL 18의 `EXPLAIN`](https://www.postgresql.org/docs/18/using-explain.html)

## 3. DB는 인덱스를 어떻게 사용하고, 어떤 접근 경로를 선택하나요?

**30–60초 답변**

> B-tree로 `WHERE order_id = 123`을 조회하면 키를 따라 해당 리프 위치를 찾아 값을 읽습니다. 범위 조회라면 시작 위치를 찾고 범위가 끝날 때까지 인덱스 항목을 읽습니다. 필요한 값이 인덱스에 없으면 인덱스 항목이 가리키는 원본 행도 읽습니다. 옵티마이저는 테이블 크기와 컬럼 통계로 조건에 맞는 행 수를 추정하고, 인덱스와 원본 행을 읽는 비용을 다른 접근 경로와 비교합니다. 작은 테이블이거나 결과가 테이블의 큰 비중을 차지하면 순차 스캔이 더 저렴할 수 있습니다. [PostgreSQL 18의 `EXPLAIN`](https://www.postgresql.org/docs/18/using-explain.html) · [PostgreSQL 18의 플래너 통계](https://www.postgresql.org/docs/18/planner-stats.html)

**꼬리 질문 · 인덱스가 있는데도 순차 스캔을 선택하는 이유는 어떻게 확인하나요?**

PostgreSQL에서는 `EXPLAIN (ANALYZE, BUFFERS)`로 실제 조회를 실행해 스캔 방식, 예상·실제 행 수, 버퍼 접근을 확인할 수 있습니다. 인덱스 스캔에서는 `Index Cond`에 적힌 조건을 인덱스에서 검사하고, `Filter`에 적힌 조건은 읽어 온 행에 적용합니다. 예상 행 수가 실제와 크게 다르면 `ANALYZE`로 수집하는 통계가 최신인지와 여러 조건에 쓰인 컬럼끼리 상관관계가 있는지 확인합니다. [PostgreSQL 18의 `EXPLAIN ANALYZE`](https://www.postgresql.org/docs/18/using-explain.html#USING-EXPLAIN-ANALYZE) · [PostgreSQL 18의 확장 통계](https://www.postgresql.org/docs/18/planner-stats.html)

## 4. 클러스터형 인덱스와 비클러스터형 인덱스는 어떻게 다른가요?

**30–60초 답변**

> 행 저장형 클러스터형 인덱스는 리프에 데이터 행 자체를 저장하고 키 순서에 따라 관리합니다. 테이블의 데이터 행이 한 가지 키 순서로 조직되므로 클러스터형 인덱스는 테이블당 하나입니다. 비클러스터형 인덱스는 데이터 행과 별도로 키와 행을 찾는 위치 정보를 가지고 있어서 테이블당 여러 개를 둘 수 있습니다. 위치 정보의 형태는 엔진에 따라 다릅니다. SQL Server에서 클러스터형 테이블의 비클러스터형 인덱스는 클러스터형 키를, 힙에서는 행 식별자를 사용합니다. [Microsoft SQL Server의 클러스터형·비클러스터형 인덱스](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/clustered-and-nonclustered-indexes-described?view=sql-server-ver17) · [MySQL 8.4의 InnoDB 클러스터형·보조 인덱스](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)

**꼬리 질문 · PostgreSQL의 `CLUSTER`도 테이블의 키 순서를 계속 유지하나요?**

`CLUSTER`는 실행 시점에 선택한 인덱스 순서대로 테이블을 물리적으로 재배치합니다. 이후 삽입이나 갱신이 일어나면 그 배치가 흐트러질 수 있어, 필요하면 다시 실행해 정리합니다. [PostgreSQL 18의 `CLUSTER`](https://www.postgresql.org/docs/18/sql-cluster.html)

## 5. InnoDB의 보조 인덱스에는 무엇이 저장되고, 조회는 어떻게 하나요?

**30–60초 답변**

> InnoDB에서 기본 키가 있는 테이블은 기본 키를 클러스터형 인덱스의 키로 사용합니다. 보조 인덱스의 리프에는 선언한 인덱스 키와 해당 행의 기본 키 컬럼이 들어 있습니다. 예를 들어 `id`가 기본 키이고 `email`에 보조 인덱스가 있으면, `email`로 찾은 기본 키로 클러스터형 인덱스에서 `name` 같은 나머지 컬럼을 읽습니다. 조회에 `email`과 `id`만 필요하면 보조 인덱스가 쿼리를 커버해 원본 행 조회를 생략할 수 있습니다. 기본 키가 길면 그 값이 들어가는 보조 인덱스들의 크기도 커집니다. [MySQL 8.4의 InnoDB 클러스터형·보조 인덱스](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html) · [MySQL 8.4의 커버링 인덱스](https://dev.mysql.com/doc/refman/8.4/en/optimizing-innodb-queries.html)

**꼬리 질문 · 커버링 인덱스라면 InnoDB가 항상 보조 인덱스만 읽나요?**

커버링은 필요한 컬럼을 인덱스에서 얻을 수 있다는 뜻입니다. InnoDB는 보조 인덱스 레코드에 삭제 표시가 있거나 읽기 시점 이후에 보조 인덱스 페이지가 갱신된 경우, 어떤 버전이 보이는지 확인하기 위해 클러스터형 인덱스의 레코드와 필요하면 언두 로그를 읽습니다. [MySQL 8.4의 InnoDB 다중 버전 관리](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)

## 6. 복합 인덱스에서 컬럼 순서가 중요한 이유는 무엇인가요?

**30–60초 답변**

> `(a, b, c)` B-tree는 `a`로 먼저 정렬하고, 같은 `a` 안에서 `b`, 같은 `b` 안에서 `c`로 정렬합니다. 그래서 `a = 1 AND b = 2`는 연속된 구간을 바로 찾을 수 있고, `b = 2`만 있으면 대상이 여러 `a` 구간에 흩어집니다. 보통 앞에서부터 이어지는 동등 조건과 그다음 첫 범위 조건이 스캔할 구간을 좁힙니다. 예를 들어 `a = 1 AND b >= 10 AND c = 2`에서 `a`와 `b`가 기본 탐색 범위를 정하고, `c`는 그 범위 안에서 후보를 거르는 데 쓰일 수 있습니다. [PostgreSQL 18의 다중 컬럼 인덱스](https://www.postgresql.org/docs/18/indexes-multicolumn.html) · [MySQL 8.4의 범위 최적화](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html)

**꼬리 질문 · 선두 컬럼에 조건이 없거나 범위 조건 뒤에 있는 컬럼도 활용할 수 있나요?**

PostgreSQL 18은 비용이 유리하면 스킵 스캔을 사용할 수 있습니다. 예를 들어 `(a, b)` 인덱스에 `b = 2`만 있고 서로 다른 `a` 값이 적으면, 각 `a` 값에 대해 `b = 2` 위치를 다시 찾아 불필요한 구간을 건너뛸 수 있습니다. 오른쪽 컬럼 조건도 같은 방식으로 일부 구간을 건너뛰거나 인덱스에서 후보를 거르는 데 쓰일 수 있으므로 실행 계획을 봅니다. [PostgreSQL 18의 B-tree 스킵 스캔](https://www.postgresql.org/docs/18/indexes-multicolumn.html)

## 7. `BOOLEAN` 컬럼에 인덱스를 걸어도 효과가 있나요?

**30–60초 답변**

> 효과는 값의 종류가 두 개라는 사실보다 조회 조건에 맞는 행의 비율에 달려 있습니다. 주문의 `is_pending = true`가 전체의 1%이고 대기 주문을 자주 조회한다면 인덱스가 읽을 행을 크게 줄일 수 있습니다. 반대로 `false`가 99%인 상태에서 그 행들을 대부분 읽는다면 순차 스캔이 유리할 수 있습니다. 테넌트별 대기 주문을 시간순으로 자주 조회하면 `(tenant_id, is_pending, created_at)` 같은 복합 인덱스를 고려하고, PostgreSQL에서는 `WHERE is_pending`으로 대기 주문만 담는 부분 인덱스도 만들 수 있습니다. [PostgreSQL 18의 플래너 통계](https://www.postgresql.org/docs/18/planner-stats.html) · [PostgreSQL 18의 다중 컬럼 인덱스](https://www.postgresql.org/docs/18/indexes-multicolumn.html) · [PostgreSQL 18의 부분 인덱스](https://www.postgresql.org/docs/18/indexes-partial.html)

**꼬리 질문 · 부분 인덱스는 어떤 쿼리에 사용할 수 있나요?**

플래너가 쿼리 조건을 만족하는 행은 모두 인덱스의 조건도 만족한다고 계획 시점에 판단할 수 있어야 합니다. 예를 들어 `(tenant_id, created_at) WHERE is_pending` 부분 인덱스는 `WHERE tenant_id = $1 AND is_pending`에 쓸 수 있습니다. `is_pending` 값까지 매개변수로 바꾼 범용 계획이라면 매 실행에서 `true`라는 사실을 증명할 수 없어 그 부분 인덱스를 사용하지 못합니다. [PostgreSQL 18의 부분 인덱스 사용 조건](https://www.postgresql.org/docs/18/indexes-partial.html)

## 8. `LIKE`의 와일드카드 위치는 인덱스 사용에 어떤 영향을 주나요?

**30–60초 답변**

> `LIKE 'prefix%'`는 고정된 접두사가 있으므로, 문자열 비교 규칙이 맞는 B-tree에서 그 접두사로 시작하는 키의 탐색 범위를 정할 수 있습니다. `LIKE '%substring%'`는 문자열의 앞부분을 알 수 없고 일치 항목이 키 순서 전체에 흩어져 있어, 그 패턴으로는 B-tree의 탐색 범위를 좁힐 수 없습니다. 인덱스 전체를 읽고 패턴을 검사하는 실행 계획은 가능할 수 있습니다. PostgreSQL에서 접두사 검색에 쓸 수 있는 연산자 클래스는 정렬 규칙에 따라 달라지며, `C` 로캘 이외에서는 `text_pattern_ops` 같은 연산자 클래스를 사용할 수 있습니다. [PostgreSQL 18의 B-tree 인덱스](https://www.postgresql.org/docs/18/indexes-types.html#INDEXES-TYPES-BTREE) · [PostgreSQL 18의 패턴 연산자 클래스](https://www.postgresql.org/docs/18/indexes-opclass.html) · [MySQL 8.4의 범위 최적화](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html)

**꼬리 질문 · PostgreSQL에서 부분 문자열 검색을 빠르게 하려면 어떻게 하나요?**

`pg_trgm` 확장의 GIN 또는 GiST 인덱스는 패턴에서 연속된 세 문자의 조합을 추출해 `LIKE`나 `ILIKE`의 후보를 찾습니다. `%postgres%`처럼 추출할 조합이 많을수록 후보를 좁히기 쉽습니다. `%ab%`처럼 추출할 트라이그램이 없으면 인덱스를 사용하더라도 전체 인덱스를 스캔합니다. [PostgreSQL 18의 `pg_trgm` 인덱스 지원](https://www.postgresql.org/docs/18/pgtrgm.html#PGTRGM-INDEX)
