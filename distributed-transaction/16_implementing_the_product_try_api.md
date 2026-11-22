# Implementing the Product Try API

Try API는 주문 서비스가 저장한 분기 키와 상품 ID, 수량을 받아 예약한다. 성공 결과와 재고 변경을 같은 트랜잭션에서 커밋한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 상품 카운터와 분기 테이블을 만든다

빈 MySQL 8.4 실습 스키마에서 아래 SQL을 실행한다. 분기 키는 주문 조정자가 상품 작업마다 고유하게 발급한다. 분기 행은 상품이 없거나 Try보다 Cancel이 먼저 온 경우에도 남길 수 있게 독립적으로 저장한다. [MySQL 8.4 · CHECK Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

```sql
CREATE TABLE product_stock (
    product_id BIGINT PRIMARY KEY,
    available INT NOT NULL CHECK (available >= 0),
    reserved INT NOT NULL CHECK (reserved >= 0)
) ENGINE=InnoDB;

CREATE TABLE product_branch (
    branch_id VARBINARY(64) PRIMARY KEY,
    product_id BIGINT NOT NULL CHECK (product_id > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    phase ENUM('NEW', 'TRIED', 'REJECTED', 'CONFIRMED', 'CANCELED') NOT NULL
) ENGINE=InnoDB;
```

## 2. 분기 키를 잠근 뒤 가용 수량을 조건부 갱신한다

아래 실습 프로시저가 트랜잭션 경계를 소유한다. 열린 애플리케이션 트랜잭션 밖에서 호출한다. NEW는 같은 트랜잭션 안에서만 쓰는 상태이고, 커밋 결과는 TRIED 또는 REJECTED다. 같은 키를 다시 받으면 현재 상태를 돌려준다. CANCELED는 예약 거절로 해석한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [MySQL 8.4 · DECLARE HANDLER](https://dev.mysql.com/doc/refman/8.4/en/declare-handler.html)

```sql
DELIMITER //
CREATE PROCEDURE product_try(
    IN p_branch VARBINARY(64), IN p_product BIGINT, IN p_qty INT
)
BEGIN
    DECLARE v_product BIGINT;
    DECLARE v_qty INT;
    DECLARE v_state VARCHAR(16) DEFAULT NULL;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_branch IS NULL OR LENGTH(p_branch) = 0
       OR p_product IS NULL OR p_product < 1 OR p_qty IS NULL OR p_qty < 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invalid branch payload';
    END IF;

    START TRANSACTION;
    INSERT INTO product_branch (branch_id, product_id, quantity, phase)
    VALUES (p_branch, p_product, p_qty, 'NEW')
    ON DUPLICATE KEY UPDATE branch_id = product_branch.branch_id;

    SELECT product_id, quantity, phase INTO v_product, v_qty, v_state
    FROM product_branch WHERE branch_id = p_branch FOR UPDATE;
    IF v_state IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'unknown branch';
    END IF;
    IF v_product <> p_product OR v_qty <> p_qty THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'branch payload mismatch';
    END IF;

    IF v_state = 'NEW' THEN
        UPDATE product_stock
        SET available = available - p_qty, reserved = reserved + p_qty
        WHERE product_id = p_product AND available >= p_qty;

        IF ROW_COUNT() = 1 THEN
            SET v_state = 'TRIED';
        ELSE
            SET v_state = 'REJECTED';
        END IF;

        UPDATE product_branch SET phase = v_state WHERE branch_id = p_branch;
    END IF;
    COMMIT;
    SELECT v_state AS phase;
END//
DELIMITER ;
```

이 예에서는 상품 없음과 재고 부족을 같은 REJECTED로 저장한다. 두 이유를 구별하는 API라면 참가자 결과에 사유를 같이 저장한다. 같은 분기 키에 상품이나 수량이 달라지면 상태를 덮어쓰지 않고 충돌로 응답한다. [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)
