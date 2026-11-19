# Join Algorithms and Join Order Optimization

조인 성능은 두 입력을 결합하는 알고리즘과 어떤 입력을 먼저 줄일 수 있는지에 따라 달라진다. 조건이 같은 쿼리도 데이터 분포와 인덱스에 따라 실행 경로가 달라진다. 외부 조인처럼 행을 보존해야 하는 경우 조인 순서를 바꿀 수 있는 범위에도 제약이 있다.

## 1. 중첩 루프 조인과 해시 조인

| 알고리즘 | 동작 | 비용을 볼 지점 |
| --- | --- | --- |
| Nested Loop Join | 바깥 입력에서 한 행을 읽고 안쪽 입력에서 일치하는 행을 찾는다. | 바깥 행 수와 안쪽 탐색 반복 횟수. 안쪽 조인 키 인덱스가 있으면 개별 탐색이 줄어든다. |
| Hash Join | 한 입력의 조인 키를 메모리 해시 테이블로 만들고 다른 입력을 읽으며 대응하는 행을 찾는다. | 해시를 만드는 입력 크기와 메모리 사용량. 버퍼에 맞지 않으면 디스크 작업이 발생할 수 있다. |

MySQL에서 해시 조인과 각 입력은 `EXPLAIN FORMAT=TREE`로 확인한다. 조인 열 인덱스가 있더라도 옵티마이저는 필터와 읽기 비용을 고려한다. [Nested-Loop Join Algorithms](https://dev.mysql.com/doc/refman/8.4/en/nested-loop-joins.html) · [Hash Join Optimization](https://dev.mysql.com/doc/refman/8.4/en/hash-joins.html)

## 2. 실습 · 고객 등급별 주문 조인

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다.

```sql
EXPLAIN ANALYZE FORMAT=TREE
SELECT c.customer_id, o.order_id
FROM perf5_customers AS c
JOIN perf5_orders AS o ON o.customer_id = c.customer_id
WHERE c.tier = 'VIP';

CREATE INDEX perf5_join_order_customer ON perf5_orders (customer_id);
ANALYZE TABLE perf5_orders;

EXPLAIN ANALYZE FORMAT=TREE
SELECT c.customer_id, o.order_id
FROM perf5_customers AS c
JOIN perf5_orders AS o ON o.customer_id = c.customer_id
WHERE c.tier = 'VIP';

DROP INDEX perf5_join_order_customer ON perf5_orders;
```

계획 트리에서 고객 등급 필터가 어느 입력에 적용되는지 확인한다. 중첩 루프가 선택되면 내부 키 조회의 `loops`를 확인하고, 해시 조인이 선택되면 해시를 만드는 쪽의 실제 행 수를 본다. 쿼리의 테이블 나열 순서와 옵티마이저의 실제 접근 순서는 다를 수 있다. [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) · [EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze)
