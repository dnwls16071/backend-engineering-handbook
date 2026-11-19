# Reducing Random Access in Joins with Covering Indexes

조인 키 인덱스를 타더라도, 결과 계산에 필요한 열이 인덱스 밖에 있으면 일치하는 각 행을 추가로 조회할 수 있다. 반복 조회가 여러 클러스터드 페이지에 흩어지면 버퍼 풀에 페이지가 있는지에 따라 비용 차이가 커진다. 커버링 인덱스는 조인 조건과 집계에 사용하는 열을 같은 인덱스에서 제공해 이런 조회를 줄일 수 있다. [Clustered and Secondary Indexes](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)

## 1. VIP 고객별 주문 통계의 인덱스 설계

- 고객 인덱스 `(tier, customer_name)`은 등급 조건과 이름을 제공한다. InnoDB의 세컨더리 키에는 기본 키인 `customer_id`도 포함된다.
- 주문 인덱스 `(customer_id)`는 고객별 주문을 찾을 수 있다. `(customer_id, total_amount)`는 합계 계산에 필요한 금액도 제공한다.
- 집계 결과에 대한 정렬은 별도의 작업이다. 원본 행 조회를 줄인 뒤에도 그룹 수와 최종 정렬 비용을 확인한다.

## 2. 실습 · 조인 키 인덱스와 커버링 인덱스

실습 환경은 MySQL 8.4(InnoDB)다. [공통 실습 데이터](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)를 사용한다.

```sql
CREATE INDEX perf5_report_tier_name ON perf5_customers (tier, customer_name);
CREATE INDEX perf5_report_customer ON perf5_orders (customer_id);

EXPLAIN ANALYZE FORMAT=TREE
SELECT c.customer_id, c.customer_name, COUNT(*) AS order_count,
       SUM(o.total_amount) AS total_spent
FROM perf5_customers AS c
JOIN perf5_orders AS o ON o.customer_id = c.customer_id
WHERE c.tier = 'VIP'
GROUP BY c.customer_id, c.customer_name
ORDER BY total_spent DESC, c.customer_id ASC
LIMIT 20;

DROP INDEX perf5_report_customer ON perf5_orders;
CREATE INDEX perf5_report_customer_amount ON perf5_orders (customer_id, total_amount);
```

위 `EXPLAIN ANALYZE`를 다시 실행해 주문 접근이 커버링으로 바뀌는지 확인한다. 중첩 루프의 조회 반복 횟수가 비슷해도 각 반복의 원본 행 조회 비용은 줄 수 있다. 계획의 연산자 시간만으로 물리 디스크 읽기 횟수를 단정할 수 없으므로 물리 I/O가 조사 대상이라면 저장 엔진과 파일 I/O 지표를 함께 본다. [EXPLAIN Output Format](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) · [Performance Schema File I/O Summary Tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-file-summary-tables.html)

```sql
DROP INDEX perf5_report_customer_amount ON perf5_orders;
DROP INDEX perf5_report_tier_name ON perf5_customers;
```
