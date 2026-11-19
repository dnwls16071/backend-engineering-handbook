# MySQL DML Fundamentals and Advanced Query Patterns

INSERT, UPDATE, DELETE, SELECT를 사용할 때는 어떤 행을 읽거나 바꿀지 먼저 정한다. 이 문서의 모의 데이터는 이어지는 [조인과 쿼리 변환](19_mysql_joins_subqueries_and_query_rewrites.md), [SQL 안티패턴](20_sql_antipatterns_and_query_refactoring.md)에서도 사용한다. 실습 환경은 MySQL 8.4(InnoDB)다.

## 1. 모의 데이터 스크립트

빈 실습 스키마에서 한 번 실행한다. API 프로젝트에는 열린 작업과 완료 작업이 있고, WEB 프로젝트에는 완료 작업과 취소 작업이 있다. TOOLS 프로젝트에는 작업이 없다. 이 차이를 이용해 조인에서 행이 생기거나 빠지는 경우를 비교한다.

```sql
CREATE TABLE mysql_lab_projects (
    project_id INT PRIMARY KEY,
    project_code VARCHAR(16) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE mysql_lab_tasks (
    task_id INT PRIMARY KEY,
    project_id INT NOT NULL,
    title VARCHAR(80) NOT NULL,
    task_state VARCHAR(12) NOT NULL DEFAULT 'OPEN',
    created_at DATETIME NOT NULL,
    FOREIGN KEY (project_id) REFERENCES mysql_lab_projects (project_id),
    INDEX idx_task_project_time (project_id, created_at, task_id),
    INDEX idx_task_created (created_at)
) ENGINE = InnoDB;

CREATE TABLE mysql_lab_task_labels (
    task_id INT NOT NULL,
    label VARCHAR(24) NOT NULL,
    PRIMARY KEY (task_id, label),
    FOREIGN KEY (task_id) REFERENCES mysql_lab_tasks (task_id)
) ENGINE = InnoDB;

START TRANSACTION;
INSERT INTO mysql_lab_projects (project_id, project_code)
VALUES (1, 'API'), (2, 'WEB'), (3, 'TOOLS');

INSERT INTO mysql_lab_tasks (task_id, project_id, title, task_state, created_at)
VALUES (101, 1, 'Add metrics', 'OPEN',      '2025-03-01 09:00:00'),
       (102, 1, 'Review schema', 'DONE',    '2025-03-01 10:00:00'),
       (201, 2, 'Fix layout', 'DONE',       '2025-03-02 09:00:00'),
       (202, 2, 'Renew theme', 'CANCELLED',  '2025-03-02 10:00:00');

INSERT INTO mysql_lab_task_labels (task_id, label)
VALUES (101, 'ops'), (101, 'ops-weekly'), (102, 'review'), (201, 'ops');
COMMIT;
```

## 2. INSERT · 기본값과 업서트

넣을 열을 명시하면 데이터와 열이 어떻게 대응하는지 드러난다. 여러 행은 하나의 VALUES 절로 넣을 수 있다. 고유 키 충돌이 입력을 갱신한다는 업무 의미라면 `ON DUPLICATE KEY UPDATE`로 업서트를 표현할 수 있다. 유일 인덱스가 여러 개면 어느 제약에서 충돌할 수 있는지 검토한다. `INSERT ... SELECT`는 검증한 조회 결과를 다른 테이블에 적재할 때 쓸 수 있다. [INSERT Statement](https://dev.mysql.com/doc/refman/8.4/en/insert.html) · [INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)

```sql
START TRANSACTION;
INSERT INTO mysql_lab_tasks (task_id, project_id, title, created_at)
VALUES (103, 1, 'New endpoint', '2025-03-03 09:00:00');

INSERT INTO mysql_lab_tasks (task_id, project_id, title, created_at)
VALUES (103, 1, 'New metrics endpoint', '2025-03-03 09:00:00') AS incoming
ON DUPLICATE KEY UPDATE title = incoming.title;
ROLLBACK;
```

## 3. UPDATE와 DELETE · 행의 범위와 실행 순서

단일 행 변경은 기본 키로 대상을 좁힌다. 여러 테이블의 조건이 필요하면 UPDATE에 조인을 사용할 수 있다. 삭제 전에 같은 조건으로 대상을 읽고, 범위가 크면 안정적인 키 순서로 제한된 행을 반복 삭제하는 방식과 트랜잭션 크기를 검토한다. 외래 키가 있으면 제약에 따라 삭제 가능 여부와 연쇄 동작이 달라진다. [UPDATE Statement](https://dev.mysql.com/doc/refman/8.4/en/update.html) · [DELETE Statement](https://dev.mysql.com/doc/refman/8.4/en/delete.html)

```sql
START TRANSACTION;
UPDATE mysql_lab_tasks SET title = 'Review project schema' WHERE task_id = 102;

UPDATE mysql_lab_tasks AS t
JOIN mysql_lab_projects AS p ON p.project_id = t.project_id
SET t.task_state = 'DONE'
WHERE p.project_code = 'API' AND t.task_state = 'OPEN';

SELECT task_id FROM mysql_lab_tasks WHERE task_state = 'CANCELLED' ORDER BY task_id;
DELETE FROM mysql_lab_tasks
WHERE task_state = 'CANCELLED'
ORDER BY task_id
LIMIT 1;
ROLLBACK;
```

## 4. SELECT · 행 필터, 그룹 필터, 순위

`WHERE`는 그룹을 만들기 전 행을 필터링하고, `HAVING`은 집계된 그룹을 필터링한다. 윈도 함수는 각 행을 유지하면서 그룹별 순위나 누계를 계산할 수 있다. 순위를 조건으로 조회하려면 아래처럼 CTE로 결과를 만든 후 바깥에서 비교한다. [SELECT Statement](https://dev.mysql.com/doc/refman/8.4/en/select.html) · [Window Functions](https://dev.mysql.com/doc/refman/8.4/en/window-functions.html)

```sql
SELECT project_id, COUNT(*) AS completed_tasks
FROM mysql_lab_tasks
WHERE task_state = 'DONE'
GROUP BY project_id
HAVING COUNT(*) >= 1
ORDER BY project_id;

WITH ranked_tasks AS (
    SELECT project_id, task_id, title,
           ROW_NUMBER() OVER (
               PARTITION BY project_id ORDER BY created_at DESC, task_id DESC
           ) AS task_rank
    FROM mysql_lab_tasks
)
SELECT project_id, task_id, title
FROM ranked_tasks
WHERE task_rank = 1
ORDER BY project_id;
```
