# Data Integrity and Constraints

관계형 데이터베이스의 제약 조건은 여러 애플리케이션이나 배치가 같은 테이블에 쓰더라도 동일한 규칙을 적용한다. 기본 키로 행을 식별하고, 값의 범위와 필수 여부를 검사하며, 외래 키로 테이블 간 관계를 지킨다. 실습 환경은 MySQL 8.4의 InnoDB이며, 빈 스키마에서 실행한다.

## 1. 행의 식별과 값의 범위

무결성은 적용 대상에 따라 나눌 수 있다. 개체 무결성은 각 행을 고유하게 식별할 수 있게 한다. 도메인 무결성은 자료형, 필수 여부, 값의 범위를 제한한다. 참조 무결성은 한 테이블의 값이 다른 테이블의 행을 올바르게 가리키도록 한다.

| 규칙 | SQL 문법 | 확인할 동작 |
| --- | --- | --- |
| 행별 식별자 | `PRIMARY KEY` | 테이블당 하나이며, 여러 열로 구성할 수 있다. 해당 열은 `NULL`을 허용하지 않는다. |
| 중복 방지 | `UNIQUE` | 중복 값을 거부한다. `NULL` 처리 방식은 DBMS에 따라 달라질 수 있다. MySQL에서는 여러 `NULL`이 허용되므로 필수 식별값에는 `NOT NULL`도 선언한다. |
| 필수 값 | `NOT NULL` | 값이 반드시 있어야 하는 열에 사용한다. |
| 생략 시 사용할 값 | `DEFAULT` | 열을 생략하거나 `DEFAULT`를 지정할 때 적용된다. 잘못 입력된 값을 검증하는 역할은 제약 조건이 맡는다. |
| 값의 범위나 행 내부 관계 | `CHECK` | 조건이 `FALSE`이면 거부한다. 조건이 `NULL`로 인해 `UNKNOWN`이면 통과하므로, 필수 값에는 `NOT NULL`을 함께 둔다. |

**MySQL 공식 문서** [CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [CHECK Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html) · [Data Type Default Values](https://dev.mysql.com/doc/refman/8.4/en/data-type-defaults.html)

## 2. 외래 키와 삭제 정책

외래 키는 자식에 참조 값을 저장할 때 일치하는 부모 행이 있도록 한다. 참조가 필수라면 외래 키 열에 `NOT NULL`도 선언한다. 부모를 삭제할 수 있는지는 자식 데이터의 수명에 따라 결정한다. 다음 예제에서는 주문이 있는 고객의 삭제를 제한하고, 주문에 종속된 상세 행은 주문을 삭제할 때 함께 지운다.

```sql
CREATE TABLE db10_customers (
    customer_id INT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE db10_orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    CONSTRAINT fk_db10_order_customer FOREIGN KEY (customer_id)
        REFERENCES db10_customers (customer_id) ON DELETE RESTRICT,
    CONSTRAINT chk_db10_order_status CHECK (status IN ('PENDING', 'PAID'))
) ENGINE = InnoDB;

CREATE TABLE db10_order_items (
    order_id INT NOT NULL,
    line_no INT NOT NULL,
    quantity INT NOT NULL,
    PRIMARY KEY (order_id, line_no),
    CONSTRAINT fk_db10_item_order FOREIGN KEY (order_id)
        REFERENCES db10_orders (order_id) ON DELETE CASCADE,
    CONSTRAINT chk_db10_item_quantity CHECK (quantity > 0)
) ENGINE = InnoDB;

INSERT INTO db10_customers VALUES (1, 'buyer@example.com');
INSERT INTO db10_orders (order_id, customer_id) VALUES (10, 1);
INSERT INTO db10_order_items VALUES (10, 1, 2);
SELECT status FROM db10_orders WHERE order_id = 10;
```

`status`는 `PENDING`으로 저장된다. 다음 세 문장은 각각 실행해 실패 이유를 확인한다.

```sql
INSERT INTO db10_orders (order_id, customer_id) VALUES (11, 999);
INSERT INTO db10_order_items VALUES (10, 2, 0);
DELETE FROM db10_customers WHERE customer_id = 1;
```

첫 번째는 참조하는 부모가 없고, 두 번째는 수량 조건을 위반한다. 세 번째는 아직 주문이 고객을 참조하므로 실패한다. 아래처럼 주문을 먼저 삭제하면 주문 상세도 제거된다.

```sql
DELETE FROM db10_orders WHERE order_id = 10;
SELECT COUNT(*) AS remaining_items FROM db10_order_items WHERE order_id = 10;
```

`remaining_items`는 0이다. `ON DELETE SET NULL`은 자식 행을 남기면서 관계를 해제하며, 외래 키 열은 `NULL`을 허용해야 한다. InnoDB에서 `NO ACTION`은 `RESTRICT`와 같이 동작한다. 삭제나 변경의 파급 범위가 업무 규칙과 맞는지 확인해서 `ON DELETE`와 `ON UPDATE`를 정한다.

**MySQL 공식 문서** [FOREIGN KEY Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)
