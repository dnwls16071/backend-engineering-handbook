# Implementing the Product Cancel API

Cancel은 TRIED의 재고를 복원하고, Try 기록이 없는 경우에는 아직 확보하지 않은 재고를 건드리지 않으면서 취소 기록을 남긴다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 1. 빈 취소와 정상 취소를 한 키로 직렬화한다

아래 프로시저는 [상품 Try 스키마](16_implementing_the_product_try_api.md)를 사용한다. Cancel이 먼저 도착하면 CANCELED를 만들고, 같은 키로 다른 상품·수량을 요청하면 충돌로 처리한다. [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)

```sql
DELIMITER //
CREATE PROCEDURE product_cancel(
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
    VALUES (p_branch, p_product, p_qty, 'CANCELED')
    ON DUPLICATE KEY UPDATE branch_id = product_branch.branch_id;

    SELECT product_id, quantity, phase INTO v_product, v_qty, v_state
    FROM product_branch WHERE branch_id = p_branch FOR UPDATE;
    IF v_state IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'unknown branch';
    END IF;
    IF v_product <> p_product OR v_qty <> p_qty THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'branch payload mismatch';
    END IF;

    IF v_state = 'TRIED' THEN
        UPDATE product_stock
        SET available = available + p_qty, reserved = reserved - p_qty
        WHERE product_id = p_product AND reserved >= p_qty;
        IF ROW_COUNT() <> 1 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'reserved stock mismatch';
        END IF;
    ELSEIF v_state NOT IN ('CANCELED', 'REJECTED') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'branch cannot be canceled';
    END IF;

    SET v_state = 'CANCELED';
    UPDATE product_branch SET phase = v_state WHERE branch_id = p_branch;
    COMMIT;
    SELECT v_state AS phase;
END//
DELIMITER ;
```

취소 기록은 적어도 늦은 호출과 재시도가 도착할 수 있는 기간 동안 보존한다. 확정 뒤 환원이 필요하다면 이 Cancel과 별도의 업무 반환 계약으로 처리한다. [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
