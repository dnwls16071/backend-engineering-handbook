# Practical Database Design and Data Modeling

데이터 모델은 서비스에서 지켜야 하는 규칙과 자주 실행하는 조회를 함께 표현한다. 개념 모델에서 고객, 주문, 주문 항목의 관계를 그린 뒤 논리 모델에서 기본 키와 외래 키를 정한다. 물리 모델에서는 자료형, 제약, 인덱스를 실제 접근 패턴과 검증 결과에 맞춘다. [Database Design Fundamentals](../database-design/01_database_design_fundamentals.md) · [Physical Database Modeling](../database-design/10_physical_database_modeling.md)

## 1. 업무 규칙과 설계 패턴

| 업무 요구 | 모델에 반영하는 방법 |
| --- | --- |
| 주문 항목은 반드시 주문에 속한다. | 항목에서 주문을 외래 키로 참조한다. 주문 안에서 항목 번호를 유일하게 만든다. |
| 구매 시점의 가격을 보존한다. | 상품의 현재 가격과 별개로, 결제에 사용한 단가를 주문 항목에 기록한다. |
| 상태 변경을 추적한다. | 읽기에는 현재 상태를 사용하고, 감사나 복원에 필요한 이전 상태와 변경 시각은 이력 테이블에 기록한다. |
| 집계 화면의 읽기 비용을 줄인다. | 집계 기준이 명확하면 요약 테이블을 두고 갱신 주기와 정정 반영 방법을 정한다. |

[FOREIGN KEY Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html) · [Row Versioning and History Tables](../database-design/16_row_versioning_and_history_tables.md) · [Aggregate Table Design](../database-design/18_aggregate_table_design.md)

## 2. 인덱스와 파티션 선택

고객의 주문 이력을 최신순으로 읽는다면 `(customer_id, ordered_at DESC, order_id DESC)`를 검토한다. 고객 ID를 동등 조건으로 고정해 시각과 주문 번호 순서를 사용할 수 있다. 주문 식별자 단건 검색은 기본 키를 사용한다. 인덱스를 늘리면 쓰기 비용도 증가하므로 실제 조회별로 어느 인덱스가 필요한지 확인한다. [Multiple-Column Indexes](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html) · [ORDER BY Optimization](https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html)

시간 기준 파티션은 날짜 조건이 해당 범위를 제한할 때 불필요한 파티션 조회를 줄인다. 만료 구간을 파티션 단위로 관리해야 하는 테이블에도 적합하다. 인덱스는 읽게 된 파티션 안의 행을 찾는 데 쓰인다. MySQL의 사용자 정의 파티셔닝을 사용하는 InnoDB 테이블에는 외래 키 제약을 둘 수 없으며 다른 테이블도 그 테이블을 외래 키로 참조할 수 없다. 그래서 외래 키를 유지하는 주문 모델과 기간별로 보존하는 이벤트 모델은 서로 다른 제약을 고려한다. [Partition Pruning](https://dev.mysql.com/doc/refman/8.4/en/partitioning-pruning.html) · [Partitioning Limitations Relating to Storage Engines](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-storage-engines.html)

## 3. 실습 · 주문과 주문 항목 모델링

실습 환경은 MySQL 8.4(InnoDB)다. 다음 테이블은 주문이 존재하는 항목만 저장할 수 있고, 주문마다 같은 항목 번호가 중복될 수 없다. 이 스키마를 [CRUD 실습](14_optimizing_crud_queries_in_mysql.md)에서 사용한다.

```sql
CREATE TABLE mysql_lab_service_orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_state VARCHAR(16) NOT NULL,
    ordered_at DATETIME NOT NULL,
    version INT NOT NULL DEFAULT 0,
    INDEX idx_customer_order_history (customer_id, ordered_at DESC, order_id DESC)
) ENGINE = InnoDB;

CREATE TABLE mysql_lab_service_order_lines (
    order_id BIGINT NOT NULL,
    line_no INT NOT NULL,
    sku VARCHAR(32) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(12, 2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, line_no),
    FOREIGN KEY (order_id) REFERENCES mysql_lab_service_orders (order_id)
) ENGINE = InnoDB;
```

업무에서 고객의 존재도 데이터베이스가 보장해야 한다면 고객 테이블과의 외래 키를 추가한다. 조회에서 자주 쓰는 조건과 정렬을 먼저 고른 뒤, 실제 데이터에서 실행 계획으로 인덱스 결정을 검증한다.
