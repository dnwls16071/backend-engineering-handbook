# AUTO_INCREMENT Lock Modes in InnoDB

InnoDB의 `AUTO_INCREMENT`는 삽입 시 자동으로 번호를 할당한다. `innodb_autoinc_lock_mode`는 동시에 쓰는 문장이 번호를 할당하는 방식을 조절한다. 번호 할당 잠금과 삽입한 행을 트랜잭션이 보호하는 잠금은 수명과 목적이 다르다. [AUTO_INCREMENT Handling in InnoDB](https://dev.mysql.com/doc/refman/8.4/en/innodb-auto-increment-handling.html)

| 모드 | 번호 할당 방식 |
| --- | --- |
| `0` Traditional | INSERT 계열 문장이 일반적으로 문장 종료까지 테이블 수준의 `AUTO-INC` 잠금을 유지한다. |
| `1` Consecutive | 삽입 행 수를 미리 아는 단순 INSERT는 보통 짧은 뮤텍스로 번호를 확보한다. `INSERT ... SELECT`처럼 행 수를 미리 알기 어려운 문장은 테이블 수준의 `AUTO-INC` 잠금을 사용한다. |
| `2` Interleaved | 테이블 수준의 `AUTO-INC` 잠금 없이 할당한다. 동시 문장 사이에서 번호가 섞일 수 있다. MySQL 8.4의 기본값이다. |

실패나 롤백으로 이미 할당한 번호가 비어 있을 수 있다. 번호는 행을 식별하는 데 쓰고, 커밋 순서나 번호가 연속이어야 하는 업무 규칙은 별도로 표현한다. 문장 기반 복제가 필요한 환경에서 interleaved 모드는 재실행 시 번호 할당의 결정성을 보장하지 않으므로 복제 형식도 확인한다. [AUTO_INCREMENT Handling in InnoDB](https://dev.mysql.com/doc/refman/8.4/en/innodb-auto-increment-handling.html)

## 실습 · 현재 모드와 번호 공백 확인

실습 환경은 MySQL 8.4(InnoDB)다. 현재 설정을 조회하고 롤백 이후 새 행에 부여되는 번호를 관찰한다.

```sql
SELECT @@GLOBAL.innodb_autoinc_lock_mode, @@SESSION.binlog_format;

CREATE TABLE mysql_lab_receipts (
    receipt_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    description VARCHAR(60) NOT NULL
) ENGINE = InnoDB;

START TRANSACTION;
INSERT INTO mysql_lab_receipts (description) VALUES ('Rolled back');
SELECT LAST_INSERT_ID() AS allocated_id;
ROLLBACK;

INSERT INTO mysql_lab_receipts (description) VALUES ('Committed');
SELECT receipt_id, description FROM mysql_lab_receipts;
```
