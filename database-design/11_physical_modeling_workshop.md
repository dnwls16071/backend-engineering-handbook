# Physical Modeling Workshop

[논리 모델링 실습](08_logical_modeling_workshop.md)의 주문 모델을 실제 테이블로 옮긴다. 실습 환경은 MySQL 8.4의 InnoDB다. SQL 블록은 빈 실습 스키마의 한 세션에서 위에서부터 실행한다. 금액은 단일 통화를 전제로 하며, 예제의 날짜·시각은 UTC로 입력한다.

## 1. 테이블 정의와 접근 패턴

| 테이블 | 행의 단위와 주요 제약 |
| --- | --- |
| `shop_members` | 회원 한 명. 이메일은 필수이며 중복을 허용하지 않는다. |
| `shop_products` | 상품 하나. 현재 가격은 0 이상이다. |
| `shop_orders` | 회원이 생성한 주문 한 건. 조회용 총액과 주문 시각을 기록한다. |
| `shop_order_items` | 주문의 한 줄. `(order_id, line_no)`가 고유하며, 주문 시점의 단가와 수량을 보존한다. |
| `shop_payments` | 해당 주문의 성공한 결제 한 건. 결제 행이 생기기 전에는 0건일 수 있다. |
| `shop_shipments` | 해당 주문의 출고 한 건. 출고하기 전에는 0건일 수 있다. |

회원별 최신 주문 조회에는 `(member_id, ordered_at DESC, order_id DESC)`를 사용 후보로 둔다. 주문 상세 조회는 `(order_id, line_no)` 고유 제약의 인덱스를 활용할 수 있어 같은 접두어의 인덱스를 중복으로 만들 필요가 있는지 확인한다. MySQL InnoDB는 자식 외래 키의 앞쪽 열과 일치하는 인덱스를 요구하며, 적합한 인덱스가 없으면 생성한다. [CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [외래 키 인덱스 요건](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html) · [정렬 최적화](https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html)

```sql
CREATE TABLE shop_members (
    member_id BIGINT PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE shop_products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(120) NOT NULL,
    current_price DECIMAL(12, 2) NOT NULL CHECK (current_price >= 0)
) ENGINE = InnoDB;

CREATE TABLE shop_orders (
    order_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL,
    ordered_at DATETIME(6) NOT NULL,
    total_amount DECIMAL(18, 2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    CONSTRAINT fk_shop_order_member FOREIGN KEY (member_id)
        REFERENCES shop_members (member_id),
    INDEX idx_shop_order_member_recent (member_id, ordered_at DESC, order_id DESC)
) ENGINE = InnoDB;

CREATE TABLE shop_order_items (
    order_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    line_no INT NOT NULL CHECK (line_no > 0),
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price_at_order DECIMAL(12, 2) NOT NULL CHECK (unit_price_at_order >= 0),
    CONSTRAINT uq_shop_item_line UNIQUE (order_id, line_no),
    CONSTRAINT fk_shop_item_order FOREIGN KEY (order_id)
        REFERENCES shop_orders (order_id),
    CONSTRAINT fk_shop_item_product FOREIGN KEY (product_id)
        REFERENCES shop_products (product_id)
) ENGINE = InnoDB;

CREATE TABLE shop_payments (
    payment_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE,
    amount DECIMAL(18, 2) NOT NULL CHECK (amount >= 0),
    paid_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_shop_payment_order FOREIGN KEY (order_id)
        REFERENCES shop_orders (order_id)
) ENGINE = InnoDB;

CREATE TABLE shop_shipments (
    shipment_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE,
    shipping_address VARCHAR(255) NOT NULL,
    shipped_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_shop_shipment_order FOREIGN KEY (order_id)
        REFERENCES shop_orders (order_id)
) ENGINE = InnoDB;
```

결제와 배송의 외래 키는 각 레코드가 기존 주문을 가리키게 한다. `UNIQUE`는 주문당 각 행을 최대 하나로 제한한다. 출고가 성공한 결제 이후여야 한다는 규칙과 확정된 주문에 항목이 하나 이상 있어야 한다는 규칙은 이 DDL의 행·참조 제약만으로 표현되지 않는다. 예제는 주문과 항목을 같은 트랜잭션에 저장한다. 출고 단계에서는 성공한 결제의 존재를 확인한 뒤 출고 행을 등록하도록 쓰기 경로를 구현한다.

## 2. 주문 시점 가격과 조회용 총액 구분하기

주문 항목에는 당시 단가를 복사하고, 주문의 조회용 총액은 그 단가에 수량을 곱한 합계로 갱신한다. 결제의 `amount`는 실제 결제된 금액이며 주문 항목을 계산한 결과와 의미가 다르다. 이 실습에서 두 값이 같은 주문은 할인이나 배송비가 없는 주문이다.

```sql
INSERT INTO shop_members VALUES (1, 'member@example.com');
INSERT INTO shop_products VALUES (10, 'Notebook', 12.50), (20, 'Pen', 9.40);

START TRANSACTION;

INSERT INTO shop_orders (order_id, member_id, ordered_at) VALUES
    (100, 1, '2026-02-01 10:00:00'),
    (101, 1, '2026-02-02 11:30:00');

INSERT INTO shop_order_items
    (order_id, line_no, product_id, quantity, unit_price_at_order)
VALUES
    (100, 1, 10, 2, 12.50),
    (100, 2, 20, 1, 9.40),
    (101, 1, 10, 1, 12.50);

UPDATE shop_orders AS o
SET total_amount = (
    SELECT SUM(i.quantity * i.unit_price_at_order)
    FROM shop_order_items AS i
    WHERE i.order_id = o.order_id
)
WHERE o.order_id IN (100, 101);

INSERT INTO shop_payments VALUES (200, 100, 34.40, '2026-02-01 10:01:00');
INSERT INTO shop_shipments VALUES
    (300, 100, '25 Market Street', '2026-02-01 15:00:00');

COMMIT;

UPDATE shop_products SET current_price = 15.00 WHERE product_id = 10;

SELECT i.order_id, i.line_no, i.unit_price_at_order, p.current_price
FROM shop_order_items AS i
JOIN shop_products AS p ON p.product_id = i.product_id
WHERE i.order_id = 100 AND i.line_no = 1;
```

상품 10의 현재가는 15.00이고 주문 100의 첫 항목 단가는 12.50이다. 조회용 총액을 유지하기로 했다면 항목을 수정하는 모든 경로에서 항목과 총액을 함께 저장해야 한다. 동시에 같은 주문을 변경할 수 있다면 주문 행을 잠그는 순서와 집계 시 읽기 범위를 정하고, 병행 실행에서 총액이 어긋나지 않는지 검증한다. [MySQL 트랜잭션 제어](https://dev.mysql.com/doc/refman/8.4/en/commit.html) · [잠금 읽기](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

## 3. 조회 결과, 실행 계획, 실제 스키마 확인하기

```sql
EXPLAIN
SELECT order_id, ordered_at, total_amount
FROM shop_orders
WHERE member_id = 1
ORDER BY ordered_at DESC, order_id DESC
LIMIT 10;

SELECT o.order_id, o.total_amount, p.amount AS paid_amount, s.shipped_at
FROM shop_orders AS o
LEFT JOIN shop_payments AS p ON p.order_id = o.order_id
LEFT JOIN shop_shipments AS s ON s.order_id = o.order_id
WHERE o.member_id = 1
ORDER BY o.ordered_at DESC, o.order_id DESC;

SELECT o.order_id
FROM shop_orders AS o
LEFT JOIN shop_order_items AS i ON i.order_id = o.order_id
GROUP BY o.order_id, o.total_amount
HAVING COUNT(i.order_item_id) = 0
    OR o.total_amount <> COALESCE(SUM(i.quantity * i.unit_price_at_order), 0);

SHOW CREATE TABLE shop_order_items;
```

최신 주문 101은 총액이 12.50이며 결제와 출고 열은 `NULL`이다. 주문 100의 총액과 결제액은 모두 34.40이다. 항목 누락이나 총액 불일치를 찾는 조회는 0행을 반환한다. 샘플 데이터가 작으므로 회원별 조회에서 인덱스가 선택되는지는 보장되지 않는다. 운영과 비슷한 데이터량과 분포에서 실제 계획을 비교한다.

`SHOW CREATE TABLE`로 고유 제약, 외래 키, 자동 생성된 인덱스를 확인한다. 모델링 도구의 역공학 기능으로 물리 ERD를 만들면 배포한 스키마의 참조 관계를 볼 수 있다. 항목이 하나 이상이어야 한다는 업무 규칙처럼 DDL에 없는 조건은 개념 모델 및 정의서에서도 확인한다. [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html) · [SHOW CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/show-create-table.html) · [MySQL Workbench 스키마 역공학](https://dev.mysql.com/doc/workbench/en/wb-reverse-engineer-live.html)
