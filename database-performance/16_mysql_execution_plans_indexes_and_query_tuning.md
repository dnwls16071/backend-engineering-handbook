# MySQL Execution Plans, Indexes, and Query Tuning

[공통 고객·주문 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)에서 추정 계획, 실제 처리 행, 쿼리 결과를 함께 비교한다. 아래 순서로 진행하면 같은 주문 조회에서 접근 경로를 바꾼 효과를 확인할 수 있다.

## 1. EXPLAIN 컬럼 읽기

| 컬럼 | 읽는 방법 |
| --- | --- |
| `table`, `type` | 처리할 테이블과 접근 유형을 본다. `ALL`은 테이블 스캔, `range`는 인덱스 범위 접근이다. |
| `possible_keys`, `key`, `key_len` | 접근에 고려한 후보, 선택한 인덱스, 사용한 키 길이를 본다. 형식이나 NULL 가능 여부에 따라 같은 열의 바이트 수가 다를 수 있다. |
| `ref`, `rows`, `filtered` | 인덱스와 비교하는 값, 읽을 행의 추정치, 테이블 조건을 통과할 비율의 추정치를 본다. |
| `Extra` | `Using index`는 커버링 조회, `Using index condition`은 인덱스 조건 푸시다운을 나타낸다. |

MySQL 8.4에서 표 형태가 필요하면 `EXPLAIN FORMAT=TRADITIONAL`을 명시한다. [MySQL EXPLAIN 출력](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)

## 2. EXPLAIN ANALYZE로 실제 실행 확인하기

`EXPLAIN ANALYZE`는 대상 문장을 실행한다. 읽기 전용 실습에서 연산자별 `actual time`의 밀리초 값, 실제 반환 행, `loops`를 확인한다. 반복 횟수가 1보다 크면 시간과 행 수를 반복당 값으로 해석한다. 상위 연산자 시간에는 하위 연산자 시간이 포함되므로 전체 트리의 시간을 합산하면 중복된다. [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze)

## 3. 풀 스캔, filesort, 내부 임시 테이블

풀 스캔은 조건에 맞는 인덱스가 없거나, 많은 행을 읽어야 해 순차 접근 비용이 더 낮을 때 선택될 수 있다. `Using filesort`는 결과 순서를 만들기 위한 추가 정렬이며, 반드시 디스크에서 정렬했다는 의미는 아니다. `Using temporary`는 중간 결과를 내부 임시 테이블로 물질화하는 경로를 나타낸다. 대표 조건에서 처리한 행 수와 시간으로 개선이 필요한지 판단한다. [MySQL EXPLAIN 출력](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) · [MySQL ORDER BY 최적화](https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html)

## 4. 조인 순서와 옵티마이저

내부 조인의 SQL 작성 순서와 계획의 실제 접근 순서는 달라질 수 있다. 옵티마이저는 각 테이블의 예상 행 수와 인덱스 접근 비용, 가능한 조인 방식을 비교한다. 외부 조인은 결과의 NULL 보존 의미 때문에 순서 변경에 제약이 있다. 아래 조인의 계획에서 고객 조건을 처리하는 시점과 주문 접근의 반복 횟수를 확인한다. [MySQL 외부 조인 최적화](https://dev.mysql.com/doc/refman/8.4/en/outer-join-optimization.html) · [조인 순서와 알고리즘](11_join_algorithms_and_join_order_optimization.md)

```sql
EXPLAIN ANALYZE
SELECT c.customer_id, o.order_id
FROM perf5_customers AS c
JOIN perf5_orders AS o ON o.customer_id = c.customer_id
WHERE c.tier = 'VIP' AND o.status = 'RETURNED';
```

## 5. 복합 인덱스 열 순서 설계하기

고객과 상태를 등호로 제한하고 주문 시각과 ID로 정렬하는 한 쿼리에는 `(customer_id, status, ordered_at DESC, order_id DESC)`를 시험한다. 인덱스의 선두 열부터 조건을 적용할 수 있고, 동률인 주문 시각은 ID로 순서를 정한다. 여러 쿼리가 인덱스를 공유한다면 가장 선택적인 컬럼 하나만 보고 정하지 말고 선두 열을 재사용하는 조회와 쓰기 비용도 함께 비교한다. [MySQL 복합 인덱스](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html)

## 6. 커버링 인덱스와 정렬·그룹화

조회에 필요한 값을 인덱스만으로 읽을 수 있으면 기본 행 조회를 줄인다. 인덱스가 조회 열을 모두 가지고 있어도 `ORDER BY` 또는 `GROUP BY`에 필요한 순서를 제공하는지는 별도로 확인한다. 예를 들어 위 인덱스는 고객과 상태를 모두 고정하면 주문 시각 순서를 제공할 수 있지만, 상태를 생략하면 여러 상태 구간을 읽어 전체 주문 시각 순서로 합치는 작업이 필요할 수 있다. [MySQL ORDER BY 최적화](https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html) · [MySQL GROUP BY 최적화](https://dev.mysql.com/doc/refman/8.4/en/group-by-optimization.html)

## 7. 인덱스 접근이 막히거나 비싸지는 일곱 가지 패턴

| 패턴 | 비교할 표현이나 판단 기준 |
| --- | --- |
| `DATE(ordered_at) = ...` | 시작 이상·다음 날 미만의 범위 조건이나 함수 기반 인덱스를 비교한다. |
| 문자열 컬럼을 숫자와 비교 | 파라미터 타입을 컬럼 타입에 맞춘다. |
| `LIKE '%term'` | 선행 와일드카드가 필요한 검색에는 컬럼의 일반 B-tree에서 접두 범위를 만들 수 없다. |
| 복합 인덱스의 선두 열 생략 | 방언의 skip scan 조건과 실제 선택 여부를 확인한다. |
| 인덱스 컬럼에 산술식 적용 | 타입과 오버플로 의미를 확인한 뒤 입력 쪽 값을 변환할 수 있는지 검토한다. |
| 일부 OR 분기에 유효한 접근 경로가 없음 | 각 분기의 선택도와 Index Merge 가능성을 본다. 분리할 때 중복과 NULL 의미도 확인한다. |
| 조건이 테이블 대부분을 반환 | 보조 인덱스와 반복 행 조회 비용을 풀 스캔과 비교한다. |

정렬·필터·커버링에서 인덱스가 맡는 역할이 다르므로 `key` 표시만으로 읽은 범위를 단정하지 않는다. [MySQL 범위 최적화](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [MySQL 타입 변환](https://dev.mysql.com/doc/refman/8.4/en/type-conversion.html)

## 8. 서브쿼리 재작성과 키셋 페이지네이션

`EXISTS`는 매칭하는 주문이 여러 개여도 고객을 한 번 반환한다. 일반 조인으로 바꾼다면 주문의 고객 키를 먼저 중복 제거해야 원래 행 수가 유지된다. 옵티마이저가 이미 세미 조인을 선택할 수 있으므로 변환 전후의 결과와 계획을 비교한다. [MySQL 세미 조인 최적화](https://dev.mysql.com/doc/refman/8.4/en/semijoins-antijoins.html)

깊은 `OFFSET` 대신 앞 페이지 마지막 행의 `(ordered_at, order_id)`를 커서로 사용한다. 최신순이라면 다음 페이지는 `ordered_at < :last_at OR (ordered_at = :last_at AND order_id < :last_id)`에 같은 필터와 정렬을 적용한다. 임의 페이지 번호가 필요한 경우와 조회 사이에 값이 변하는 경우의 동작도 요구사항에 맞춰 판단한다. [MySQL 키셋 페이지네이션](../mysql/10_keyset_pagination_without_offset.md)

## 9. ORM의 N+1 찾기와 해결하기

주문 목록 1건의 SQL 뒤 동일 형태의 관계 조회가 주문마다 반복되는지 한 요청의 쿼리 로그나 추적에서 확인한다. `N+1`의 개수는 1차 캐시에 이미 있는 엔티티와 조회 범위에 따라 달라질 수 있다. 화면에 필요한 값만 DTO로 투영하거나 to-one fetch join을 적용한다. 부모 목록을 페이징하면서 to-many를 가져올 때는 부모 ID 페이지를 먼저 구하고 필요한 관계를 함께 읽으면 컬렉션으로 인해 부모 페이지가 부풀어 오르는 문제를 피할 수 있다. [Hibernate 페치 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching) · [두 단계 조회 예제](../high-performance-spring-persistence/07_fetching_pagination_projections_and_query_plans.md)

## 10. 실습 · 실행 계획의 기준값 기록하기

```sql
EXPLAIN FORMAT=TRADITIONAL
SELECT order_id, ordered_at
FROM perf5_orders
WHERE customer_id = 42 AND status = 'PAID'
ORDER BY ordered_at DESC, order_id DESC
LIMIT 5;

EXPLAIN ANALYZE
SELECT order_id, ordered_at
FROM perf5_orders
WHERE customer_id = 42 AND status = 'PAID'
ORDER BY ordered_at DESC, order_id DESC
LIMIT 5;
```

인덱스와 추정 행 수, 실제 읽은 행, 정렬 유무를 기록한다. 실제 SELECT의 결과 ID와 표시 순서도 저장한다.

## 11. 실습 · 복합 인덱스 추가 후 비교하기

```sql
CREATE INDEX ix_perf5_workload_order
    ON perf5_orders (customer_id, status, ordered_at DESC, order_id DESC);

ANALYZE TABLE perf5_orders;
```

10절의 두 계획과 SELECT 결과를 다시 확인한다. 반환한 ID와 순서는 같아야 한다. 접근 경로와 정렬, 실제 읽은 행 수를 비교한다. 실습을 마치면 추가한 인덱스만 제거한다.

```sql
DROP INDEX ix_perf5_workload_order ON perf5_orders;
```
