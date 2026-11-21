# Error Handling in MySQL Stored Programs

`DECLARE ... HANDLER`는 저장 프로그램 블록 안에서 특정 오류 코드, `SQLSTATE`, 또는 조건 분류에 대응한다. `CONTINUE`는 처리한 뒤 해당 문장 다음부터 실행을 이어 가고, `EXIT`는 핸들러를 선언한 블록에서 빠져나온다. `NOT FOUND`는 커서의 마지막 행이나 결과가 없는 `SELECT ... INTO`의 조건을 처리할 때 쓴다. [MySQL DECLARE HANDLER](https://dev.mysql.com/doc/refman/8.4/en/declare-handler.html)

## 트랜잭션을 소유하는 프로시저 예제

다음 예제에서는 호출자가 열린 트랜잭션 없이 프로시저를 호출한다. `START TRANSACTION`은 이미 열려 있는 트랜잭션을 암시적으로 커밋하므로, 호출자가 트랜잭션을 관리하는 구조에서는 프로시저의 시작·종료 책임을 함께 설계한다. `DELIMITER`는 `mysql` 클라이언트 지시자다. [암시적 커밋](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html) · [mysql 클라이언트 명령](https://dev.mysql.com/doc/refman/8.4/en/mysql-commands.html)

```sql
DELIMITER //
CREATE PROCEDURE start_job(IN p_job_id BIGINT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    UPDATE jobs
    SET status = 'RUNNING'
    WHERE job_id = p_job_id AND status = 'READY';

    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Job is not ready';
    END IF;

    COMMIT;
END//
DELIMITER ;
```

`SIGNAL`은 호출자에게 명시적인 업무 오류를 전달한다. `RESIGNAL`은 실패 원인을 유지하면서 상위 호출자에게 전달한다. 핸들러 안에서 원래 조건의 진단 정보가 필요하면 `GET STACKED DIAGNOSTICS`를 사용해 현재 진단 영역과 구분한다. [MySQL SIGNAL](https://dev.mysql.com/doc/refman/8.4/en/signal.html) · [MySQL RESIGNAL](https://dev.mysql.com/doc/refman/8.4/en/resignal.html) · [MySQL GET DIAGNOSTICS](https://dev.mysql.com/doc/refman/8.4/en/get-diagnostics.html)
