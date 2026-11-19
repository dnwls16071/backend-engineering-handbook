# Stored Procedures, Functions, and Triggers

관계형 데이터베이스에 저장한 코드를 애플리케이션이 호출하거나 특정 변경 시점에 자동으로 실행할 수 있다. 호출자가 어떤 결과를 받는지, 어떤 쓰기가 추가로 발생하는지, 어떤 권한으로 실행되는지부터 확인한다. 실습 환경은 MySQL 8.4의 InnoDB다.

## 1. 실행 방식과 용도

| 객체 | 실행 방식 | 용도 |
| --- | --- | --- |
| 저장 프로시저 | 애플리케이션이나 다른 루틴이 이름으로 명시적으로 호출한다. DBMS가 제공하는 매개변수와 결과 집합으로 값을 주고받는다. | 여러 단계의 데이터 처리 |
| 저장 함수 | SQL 표현식에서 호출하고 그 결과를 조회나 계산에 사용한다. 반환 가능한 형태는 DBMS에 따라 다르다. | 여러 쿼리에서 같은 계산을 재사용 |
| 트리거 | 테이블 변경 같은 지정된 이벤트에 자동으로 실행한다. 실행 시점과 행·문장 단위 지원은 DBMS에 따라 다르다. | 쓰기 경로와 관계없이 같은 변경 이벤트에서 수행해야 하는 처리 |

MySQL에서 프로시저는 `CALL`로 호출하며 `IN`, `OUT`, `INOUT`을 사용할 수 있다. 저장 함수는 `RETURNS`로 선언한 값 하나를 반환한다. 트리거는 영향을 받은 각 행의 `BEFORE` 또는 `AFTER` 시점에 실행한다. `INSERT`는 `NEW`, `DELETE`는 `OLD`, `UPDATE`는 둘 다 사용할 수 있다. InnoDB 테이블에 대한 트리거의 변경은 원래 문장의 트랜잭션에 포함된다. [CREATE PROCEDURE and CREATE FUNCTION](https://dev.mysql.com/doc/refman/8.4/en/create-procedure.html) · [Trigger Syntax](https://dev.mysql.com/doc/refman/8.4/en/trigger-syntax.html)

## 2. 조회, 계산, 재고 변경 기록 실습

저장 루틴과 트리거 생성 권한이 있는 빈 스키마에서 실행한다. 이 블록의 `DELIMITER`는 `mysql` 클라이언트가 루틴 본문의 세미콜론을 문장 끝으로 오인하지 않게 하는 클라이언트 명령이다.

```sql
CREATE TABLE db12_products (
    product_id INT PRIMARY KEY,
    stock INT NOT NULL CHECK (stock >= 0)
) ENGINE = InnoDB;

CREATE TABLE db12_stock_audit (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    previous_stock INT NOT NULL,
    current_stock INT NOT NULL
) ENGINE = InnoDB;

INSERT INTO db12_products VALUES (7, 12);

DELIMITER //

CREATE PROCEDURE db12_find_stock(IN p_id INT, OUT p_stock INT)
READS SQL DATA
SQL SECURITY INVOKER
BEGIN
    SELECT MAX(stock) INTO p_stock
    FROM db12_products
    WHERE product_id = p_id;
END//

CREATE FUNCTION db12_amount_with_tax(p_amount DECIMAL(10, 2), p_tax_pct DECIMAL(5, 2))
RETURNS DECIMAL(12, 2)
DETERMINISTIC
NO SQL
SQL SECURITY INVOKER
RETURN ROUND(p_amount * (1 + p_tax_pct / 100), 2)//

CREATE TRIGGER db12_log_stock_update
AFTER UPDATE ON db12_products
FOR EACH ROW
BEGIN
    IF OLD.stock <> NEW.stock THEN
        INSERT INTO db12_stock_audit (product_id, previous_stock, current_stock)
        VALUES (NEW.product_id, OLD.stock, NEW.stock);
    END IF;
END//

DELIMITER ;

CALL db12_find_stock(7, @stock);
SELECT @stock AS stock;
SELECT db12_amount_with_tax(80.00, 7.50) AS total;

START TRANSACTION;
UPDATE db12_products SET stock = 10 WHERE product_id = 7;
ROLLBACK;
SELECT COUNT(*) AS rolled_back_audit_rows FROM db12_stock_audit;

UPDATE db12_products SET stock = 9 WHERE product_id = 7;
SELECT product_id, previous_stock, current_stock FROM db12_stock_audit;
```

조회 프로시저는 재고 12를 돌려주고, 계산 함수는 86.00을 반환한다. 첫 변경을 롤백하면 감사 행도 함께 사라져 집계는 0이다. 마지막 변경에서는 상품 7의 재고가 12에서 9로 바뀌며 감사 행 하나가 남는다. 마지막 변경은 기본 `autocommit` 동작을 전제로 한다. [Defining Stored Programs](https://dev.mysql.com/doc/refman/8.4/en/stored-programs-defining.html) · [Trigger Syntax](https://dev.mysql.com/doc/refman/8.4/en/trigger-syntax.html)

## 3. 권한과 관리 범위

MySQL의 프로시저와 함수는 `SQL SECURITY INVOKER`로 호출자의 권한을 적용하거나 `DEFINER`의 권한으로 실행할 수 있다. 트리거의 실행 권한은 `DEFINER`를 기준으로 확인한다. 바이너리 로그 설정에 따라 함수나 트리거 생성에 추가 권한 또는 선언 조건이 적용될 수 있다. [Stored Object Access Control](https://dev.mysql.com/doc/refman/8.4/en/stored-objects-security.html) · [Stored Program Binary Logging](https://dev.mysql.com/doc/refman/8.4/en/stored-programs-logging.html)

업무 흐름을 데이터베이스 객체에 넣으면 호출 관계, 자동 실행되는 쓰기, 배포 순서를 애플리케이션 코드와 함께 추적해야 한다. 검증을 제약 조건으로 표현할 수 있다면 DDL에 두고, 변경이 잦은 업무 흐름은 애플리케이션 트랜잭션에서 표현할 수 있다. 저장 객체를 선택했다면 정의를 마이그레이션으로 관리하고 테스트에서 호출 결과와 부수 효과를 함께 확인한다.
