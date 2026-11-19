# Reproducing and Handling InnoDB Deadlocks

교착 상태는 트랜잭션들이 서로가 가진 잠금을 기다려 대기 관계가 순환할 때 발생한다. InnoDB의 교착 상태 감지가 켜져 있으면 교착을 끊기 위해 트랜잭션 하나를 롤백한다. 애플리케이션은 해당 오류(`1213`)를 받으면 업무 트랜잭션 전체를 처음부터 다시 시도할 수 있어야 한다. 기본 설정에서 잠금 대기 시간 초과(`1205`)는 시간 초과가 난 문장만 롤백하므로 두 오류의 처리 범위를 구분한다. [Deadlocks in InnoDB](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html) · [InnoDB Error Handling](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)

## 실습 · 두 행을 반대 순서로 갱신

실습 환경은 MySQL 8.4(InnoDB)다. 같은 실습 스키마에 연결된 세션 두 개를 준비한다. 초기화는 한 세션에서 실행한다.

```sql
CREATE TABLE mysql_lab_stock (
    item_id INT PRIMARY KEY,
    quantity INT NOT NULL
) ENGINE = InnoDB;

INSERT INTO mysql_lab_stock VALUES (101, 10), (102, 10);
COMMIT;
```

| 순서 | 세션 | SQL |
| --- | --- | --- |
| 1 | A | `START TRANSACTION;` 다음에 `UPDATE mysql_lab_stock SET quantity = quantity + 1 WHERE item_id = 101;` |
| 2 | B | `START TRANSACTION;` 다음에 `UPDATE mysql_lab_stock SET quantity = quantity + 1 WHERE item_id = 102;` |
| 3 | A | `UPDATE mysql_lab_stock SET quantity = quantity + 1 WHERE item_id = 102;` 실행 후 대기 |
| 4 | B | `UPDATE mysql_lab_stock SET quantity = quantity + 1 WHERE item_id = 101;` 실행 후 교착 감지 |
| 5 | A, B | 두 세션에서 각각 `ROLLBACK;`으로 마무리 |

감지 후 어느 쪽이 취소될지는 정해져 있지 않다. 권한이 있는 세션에서 `SHOW ENGINE INNODB STATUS`의 `LATEST DETECTED DEADLOCK` 항목을 보면 대기한 문장과 잠금을 확인할 수 있다. [How to Minimize and Handle Deadlocks](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html)

## 발생 가능성을 줄이는 방법

같은 종류의 작업은 같은 순서로 키를 처리한다. 조건에 맞는 인덱스로 탐색 범위를 줄이고 트랜잭션을 짧게 유지한다. 재시도는 횟수를 제한하고 잠깐 간격을 둔다. 트랜잭션 안에서 외부 요청이나 메시지 발행이 함께 일어난다면 재시도 시 부수 효과가 겹치지 않도록 처리한다.
