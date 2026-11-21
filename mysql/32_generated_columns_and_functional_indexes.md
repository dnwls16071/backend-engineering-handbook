# Generated Columns and Functional Indexes

생성 컬럼은 다른 열을 사용한 계산 결과를 스키마에 정의한다. `VIRTUAL`은 클러스터형 레코드에 값을 보관하지 않고 필요할 때 계산하며, `STORED`는 쓰기 시 계산한 값을 저장한다. InnoDB는 가상 컬럼에도 보조 인덱스를 만들 수 있고, 그 인덱스에는 계산된 키가 저장된다. [MySQL 생성 컬럼](https://dev.mysql.com/doc/refman/8.4/en/create-table-generated-columns.html) · [InnoDB 가상 컬럼 보조 인덱스](https://dev.mysql.com/doc/refman/8.4/en/create-table-secondary-indexes.html)

## 계산 결과가 조회에 필요할 때

```sql
CREATE TABLE invoice_lines_example (
    line_id BIGINT PRIMARY KEY,
    unit_price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(20, 2)
        GENERATED ALWAYS AS (unit_price * quantity) VIRTUAL,
    INDEX ix_invoice_subtotal (subtotal)
) ENGINE = InnoDB;

SELECT line_id, subtotal
FROM invoice_lines_example
WHERE subtotal >= 100.00;
```

## 조회 조건에만 표현식을 사용할 때

스키마에 이름 있는 컬럼을 추가할 필요가 없다면, 예를 들어 `orders(created_at)`의 날짜 표현식에 직접 인덱스를 둘 수 있다.

```sql
CREATE INDEX ix_orders_created_date ON orders ((DATE(created_at)));

EXPLAIN
SELECT order_id
FROM orders
WHERE DATE(created_at) = DATE '2026-11-20';
```

예제는 `created_at`이 `DATETIME`인 경우다. 함수 기반 키는 내부적으로 숨겨진 가상 생성 컬럼에 구현된다. 표현식과 결과 타입이 인덱스 정의와 어떻게 일치하는지 확인하며, 저장 함수나 서브쿼리처럼 생성 컬럼 제약에 걸리는 표현식은 사용할 수 없다. 이미 `created_at`에 인덱스가 있다면 날짜를 시작·종료 범위로 표현하는 쿼리도 함께 비교한다. [MySQL 함수 기반 키](https://dev.mysql.com/doc/refman/8.4/en/create-index.html) · [생성 컬럼 인덱스의 표현식 일치 조건](https://dev.mysql.com/doc/refman/8.4/en/generated-column-index-optimizations.html)
