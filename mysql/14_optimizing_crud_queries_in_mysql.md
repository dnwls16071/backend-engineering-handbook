# Optimizing CRUD Queries in MySQL

CRUD의 Create는 `INSERT`로 행을 추가하는 작업이다. `CREATE TABLE`은 테이블 구조를 정의하는 DDL이다. CRUD를 튜닝할 때는 읽기 범위와 반환량, 쓰기가 변경하는 행의 수와 트랜잭션 범위를 확인한다. 실습 환경은 MySQL 8.4(InnoDB)이며 [13번의 주문 테이블](13_practical_database_design_and_data_modeling.md)을 사용한다. [SQL Statements](https://dev.mysql.com/doc/refman/8.4/en/sql-statements.html)

## 1. INSERT · 필요한 행을 한 번에 기록

함께 저장되어야 하는 주문과 주문 항목은 같은 트랜잭션으로 묶는다. 같은 테이블에 여러 행을 넣을 때 다중 행 INSERT로 문장 전송과 처리 횟수를 줄일 수 있다. 큰 배치는 트랜잭션과 롤백 비용도 함께 늘어나는지 측정한다. [Optimizing INSERT Statements](https://dev.mysql.com/doc/refman/8.4/en/insert-optimization.html) · [Optimizing Single-Row and Bulk Inserts](04_optimizing_single_row_and_bulk_inserts.md)

```sql
START TRANSACTION;
INSERT INTO mysql_lab_service_orders (order_id, customer_id, order_state, ordered_at)
VALUES (501, 8, 'PENDING', '2025-06-15 09:00:00'),
       (502, 8, 'PAID',    '2025-06-16 10:00:00'),
       (503, 9, 'PAID',    '2025-06-16 10:00:00');
INSERT INTO mysql_lab_service_order_lines (order_id, line_no, sku, quantity, unit_price)
VALUES (501, 1, 'MUG', 2, 12.00), (501, 2, 'TEA', 1, 8.00),
       (502, 1, 'TEA', 3, 8.00), (503, 1, 'MUG', 1, 12.00);
COMMIT;
```

## 2. SELECT · 조회 범위와 반환량 줄이기

```sql
EXPLAIN FORMAT=TREE
SELECT order_id, order_state, ordered_at
FROM mysql_lab_service_orders
WHERE customer_id = 8 AND ordered_at >= '2025-06-01' AND ordered_at < '2025-07-01'
ORDER BY ordered_at DESC, order_id DESC
LIMIT 20;
```

월별 조회 조건을 시작 시각 이상, 다음 달 시작 미만으로 표현하면 원본 시각을 범위로 탐색할 수 있다. 목록에서 쓰는 열만 선택하고, 시각이 같은 행의 순서는 주문 번호로 결정한다. 데이터가 많은 환경에서는 비용에 따라 인덱스 선택이 달라지므로 접근 경로와 읽는 행 수를 확인한다. [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [LIMIT Query Optimization](https://dev.mysql.com/doc/refman/8.4/en/limit-optimization.html)

## 3. 복합 조회 · 집계와 윈도 함수

특정 기간의 주문에 고객별 최신순 순위를 매긴 뒤 항목을 조인하고 주문별 금액을 합산한다. 순위를 주문 단위에서 먼저 계산하므로 항목이 여러 개인 주문도 한 순위만 차지한다. [Window Functions](https://dev.mysql.com/doc/refman/8.4/en/window-functions.html)

```sql
WITH ranked_orders AS (
    SELECT order_id, customer_id, ordered_at,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id ORDER BY ordered_at DESC, order_id DESC
           ) AS position_in_history
    FROM mysql_lab_service_orders
    WHERE ordered_at >= '2025-06-01' AND ordered_at < '2025-07-01'
)
SELECT r.customer_id, r.order_id, r.ordered_at, SUM(l.quantity * l.unit_price) AS total
FROM ranked_orders AS r
JOIN mysql_lab_service_order_lines AS l ON l.order_id = r.order_id
WHERE r.position_in_history <= 2
GROUP BY r.customer_id, r.order_id, r.ordered_at
ORDER BY r.customer_id, r.ordered_at DESC, r.order_id DESC;
```

## 4. UPDATE와 DELETE · 바꿀 행을 명확히 지정

```sql
UPDATE mysql_lab_service_orders
SET order_state = 'PAID', version = version + 1
WHERE order_id = 501 AND order_state = 'PENDING' AND version = 0;

DELETE FROM mysql_lab_service_order_lines
WHERE order_id = 501 AND line_no = 2;
```

UPDATE의 영향 행 수가 0이면 ID, 이전 상태, 버전 중 하나가 맞지 않은 경우다. 서비스는 다시 읽어 처리할 조건을 확인한다. DELETE는 데이터 정리 예시이며 실제 주문의 수정 또는 삭제 가능 여부는 업무 규칙에 따라 정한다. 외래 키로 연결된 주문을 정리할 때는 자식 행 처리 순서와 삭제 정책을 먼저 정한다. 대량 삭제는 키 범위별로 나누고 트랜잭션 크기, 잠금, 복제 지연을 확인한다. [UPDATE Statement](https://dev.mysql.com/doc/refman/8.4/en/update.html) · [DELETE Statement](https://dev.mysql.com/doc/refman/8.4/en/delete.html)
