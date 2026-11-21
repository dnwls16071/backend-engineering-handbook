# Join Algorithms and Query Performance

SQL의 조인 유형은 결과에 포함할 행을 정한다. PostgreSQL 18 옵티마이저는 같은 결과를 만드는 접근 경로와 조인 순서를 검토하고, 통계와 비용 추정에 따라 실행 계획을 선택한다. [PostgreSQL 18 옵티마이저](https://www.postgresql.org/docs/18/planner-optimizer.html)

## 서브쿼리와 옵티마이저

`FROM`의 단순한 서브쿼리는 상위 쿼리로 펼쳐질 수 있다. 아래의 두 쿼리는 동일한 주문을 반환하고 같은 계획을 사용할 수 있다. 서브쿼리가 `LIMIT`으로 행을 먼저 고르거나 외부 조인이 일치하지 않은 행을 보존한다면, 조건의 위치나 조인 순서를 바꿨을 때 결과가 달라지는지 확인한다. [PostgreSQL 18의 명시적 조인과 서브쿼리 펼치기](https://www.postgresql.org/docs/18/explicit-joins.html)

바깥 쿼리의 값을 참조하는 상관 서브쿼리도 형태에 따라 세미 조인이나 안티 조인으로 계획될 수 있다. 실행 계획에 반복하는 `SubPlan`이 있으면 실제 `loops`와 내부 접근 비용을 함께 확인한다. 외부 참조가 없는 스칼라 서브쿼리는 `InitPlan`으로 한 번 평가될 수도 있다. [PostgreSQL 18 실행 계획의 SubPlan과 InitPlan](https://www.postgresql.org/docs/18/using-explain.html)

## 조인 알고리즘 세 가지

| 알고리즘 | 동작 | 비교할 비용 |
| --- | --- | --- |
| Nested Loop | 바깥 입력의 각 행에 대해 안쪽에서 일치하는 행을 찾는다. | 바깥 행 수와 안쪽 탐색 비용. 안쪽 조인 키에 인덱스가 있어 소수의 행을 찾는다면 반복 탐색의 비용이 낮을 수 있다. |
| Hash Join | 해시 비교가 가능한 조건에서 한쪽 입력으로 해시 테이블을 만들고, 반대쪽 키로 일치하는 행을 찾는다. | 해시를 만드는 입력의 행 수와 폭, 메모리 사용량, 배치 및 임시 파일 입출력. |
| Merge Join | 병합 비교가 가능한 조인 키 순서로 두 입력을 읽으면서 일치하는 구간을 결합한다. | 양쪽이 이미 정렬된 순서를 제공하는지, 별도 정렬이 필요한지, 중복 키에서 얼마나 많은 행이 만들어지는지. |

필터가 통과시키는 행 수, 일치하는 키의 분포, 인덱스가 제공하는 순서, 메모리 설정에 따라 같은 조인도 다른 알고리즘을 사용할 수 있다. 어느 경우든 여러 행이 같은 키를 가지면 일치하는 조합을 출력하는 비용이 생긴다. [PostgreSQL 18 계획 경로와 조인 전략](https://www.postgresql.org/docs/18/planner-optimizer.html#PLANNER-OPTIMIZER-GENERATING-POSSIBLE-PLANS)

## 실행 계획으로 비교하기

아래 실습은 고객 1만 명마다 주문 10건을 만든다. 같은 세션에서 임시 테이블과 인덱스를 만든 후 통계를 수집하고, 두 쿼리를 비교한다.

```sql
CREATE TEMP TABLE plan_demo_customers (customer_id integer PRIMARY KEY);
CREATE TEMP TABLE plan_demo_orders (order_id integer, customer_id integer NOT NULL);
INSERT INTO plan_demo_customers SELECT n FROM generate_series(1, 10000) AS s(n);
INSERT INTO plan_demo_orders
SELECT n, (n - 1) % 10000 + 1 FROM generate_series(1, 100000) AS s(n);
CREATE INDEX ON plan_demo_orders (customer_id);
ANALYZE plan_demo_customers;
ANALYZE plan_demo_orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT c.customer_id, o.order_id
FROM plan_demo_customers AS c
JOIN plan_demo_orders AS o ON o.customer_id = c.customer_id
WHERE c.customer_id BETWEEN 1 AND 20;

EXPLAIN (ANALYZE, BUFFERS)
SELECT c.customer_id, o.order_id
FROM (
    SELECT customer_id FROM plan_demo_customers WHERE customer_id BETWEEN 1 AND 20
) AS c
JOIN plan_demo_orders AS o ON o.customer_id = c.customer_id;
```

두 쿼리는 모두 200행을 반환한다. 두 상한을 모두 `10000`으로 바꾸면 10만 행을 반환한다. PostgreSQL 18.4 실습에서는 두 표현 모두 좁은 범위에서 `Nested Loop`를 선택해 안쪽 주문 인덱스를 20번 탐색했고, 넓은 범위에서는 `Hash Join`을 선택해 고객 입력으로 해시 테이블을 만들었다.

1. `cost`의 두 값은 첫 행 전까지와 끝까지 처리할 때의 예상 비용이다. 비용 단위와 `actual time`의 밀리초 단위는 서로 다르다. 예상 `rows`는 해당 노드가 한 번 실행될 때 내보낼 행 수다.
2. `actual rows`와 `actual time`은 실행 1회당 평균이다. 가령 `rows=10 loops=20`인 노드는 약 200행을 내보냈다. 예상과 실제 행 수가 크게 갈리기 시작한 노드에서 데이터 분포와 필터 추정을 확인한다. 상위 노드 시간에는 하위 작업이 포함된다.
3. `Buffers`에서 일반 테이블은 `shared`, 이 실습의 임시 테이블은 `local` 접근을 확인한다. 노드의 값에는 하위 노드가 포함된다. 해시의 `Batches`가 1보다 크거나 정렬이 `external merge`로 표시되면 `temp read/written`에서 임시 파일 작업을 확인한다.
4. 변경 전후 결과와 중복 수가 같은지 확인하고, 같은 데이터와 설정으로 캐시 상태를 맞춰 여러 번 실행해 실행 시간 및 버퍼 사용량을 비교한다. `ANALYZE` 옵션은 문장을 실제로 실행하므로 쓰기 문장을 측정할 때는 데이터 변경도 발생한다. [PostgreSQL 18 EXPLAIN 사용법](https://www.postgresql.org/docs/18/using-explain.html) · [EXPLAIN 옵션](https://www.postgresql.org/docs/18/sql-explain.html)
