# Implementing the Product Confirm API

Confirm은 조정자의 확정 결정 이후에 보낸다. 참가자의 TRIED 상태에서만 예약 수량을 소비하며 가용 수량은 Try에서 이미 변경했다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 1. 확정의 조건과 결과를 고정한다

[상품 Try 스키마](16_implementing_the_product_try_api.md)에 아래 프로시저를 추가한다. 같은 키의 CONFIRMED는 그대로 반환하고, 다른 상태 또는 알 수 없는 키를 받은 경우 실패시켜 조정자가 기록을 대조하게 한다. [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) · [MySQL 8.4 · DECLARE HANDLER](https://dev.mysql.com/doc/refman/8.4/en/declare-handler.html)

```sql
DELIMITER //
CREATE PROCEDURE product_confirm(
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
    SELECT product_id, quantity, phase INTO v_product, v_qty, v_state
    FROM product_branch WHERE branch_id = p_branch FOR UPDATE;
    IF v_state IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'unknown branch';
    END IF;
    IF v_product <> p_product OR v_qty <> p_qty THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'branch payload mismatch';
    END IF;

    IF v_state = 'TRIED' THEN
        UPDATE product_stock SET reserved = reserved - p_qty
        WHERE product_id = p_product AND reserved >= p_qty;
        IF ROW_COUNT() <> 1 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'reserved stock mismatch';
        END IF;

        SET v_state = 'CONFIRMED';
        UPDATE product_branch SET phase = v_state WHERE branch_id = p_branch;
    ELSEIF v_state <> 'CONFIRMED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'branch cannot be confirmed';
    END IF;
    COMMIT;
    SELECT v_state AS phase;
END//
DELIMITER ;
```

프로시저 커밋 후 HTTP 응답이 유실되면 같은 키로 확정한다. 재시도 결과가 CONFIRMED이고 상품 카운터는 바뀌지 않아야 한다. [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)
