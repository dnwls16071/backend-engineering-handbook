# Views

뷰는 이름을 붙인 쿼리 정의다. 일반 뷰는 조회 결과를 따로 보관하지 않고, 조회 시 보이는 데이터는 원본에 대한 트랜잭션 격리 규칙을 따른다. 여러 사용자가 같은 집계 기준을 사용하거나 원본에서 공개할 행과 열의 범위를 정할 때 유용하다.

실습 환경은 MySQL 8.4다. 예제는 비어 있는 실습 스키마에서 순서대로 실행한다. MySQL 8.4 뷰는 임시 테이블을 참조할 수 없으므로 일반 테이블을 사용한다.

## 1. 뷰 만들기, 읽기, 정의 확인하기

```sql
CREATE TABLE lab07_agents (
    agent_id INT PRIMARY KEY,
    display_name VARCHAR(40) NOT NULL,
    team_code VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    hourly_rate DECIMAL(8, 2) NOT NULL
);

INSERT INTO lab07_agents (agent_id, display_name, team_code, is_active, hourly_rate)
VALUES
    (1, 'Nari', 'support', TRUE, 32.50),
    (2, 'Owen', 'support', FALSE, 34.00),
    (3, 'Mika', 'platform', TRUE, 43.00);

CREATE VIEW lab07_active_directory AS
SELECT agent_id, display_name, team_code
FROM lab07_agents
WHERE is_active = TRUE
WITH CHECK OPTION;

CREATE VIEW lab07_team_activity AS
SELECT team_code,
       COUNT(*) AS agent_count,
       SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) AS active_count
FROM lab07_agents
GROUP BY team_code;

SELECT agent_id, display_name, team_code
FROM lab07_active_directory
ORDER BY agent_id;

SELECT team_code, agent_count, active_count
FROM lab07_team_activity
ORDER BY team_code;

SHOW CREATE VIEW lab07_team_activity;
```

활성 명단에는 1번과 3번이 나온다. 팀별 집계에서 `support`는 전체 2명, 활성 1명이고 `platform`은 전체 1명, 활성 1명이다. MySQL 8.4의 `SHOW CREATE VIEW`로 저장된 뷰 정의를 확인한다.

**공식 문서** [CREATE VIEW](https://dev.mysql.com/doc/refman/8.4/en/create-view.html) · [SHOW CREATE VIEW](https://dev.mysql.com/doc/refman/8.4/en/show-create-view.html)

## 2. 뷰의 정의 변경과 행 수정 구분하기

뷰의 정의를 바꾸는 작업과 뷰를 통해 원본 행을 수정하는 작업은 다르다. 수정할 수 있는 뷰의 조건은 DBMS마다 다르다. 아래 MySQL 8.4 예제에서 `ALTER VIEW`는 활성 명단을 `support` 팀으로 좁힌다. 이 단순 뷰의 각 행이 원본 한 행과 대응하므로 `UPDATE`로 이름을 바꾸면 원본 테이블에 반영된다.

```sql
ALTER VIEW lab07_active_directory AS
SELECT agent_id, display_name, team_code
FROM lab07_agents
WHERE is_active = TRUE AND team_code = 'support'
WITH CHECK OPTION;

UPDATE lab07_active_directory
SET display_name = 'Nari Kim'
WHERE agent_id = 1;

SELECT agent_id, display_name, team_code
FROM lab07_agents
WHERE agent_id = 1;

SELECT table_name, is_updatable
FROM information_schema.views
WHERE table_schema = DATABASE()
  AND table_name IN ('lab07_active_directory', 'lab07_team_activity')
ORDER BY table_name;
```

원본의 1번 행에 `Nari Kim`이 기록된다. 같은 뷰에서 이 행의 `team_code`를 `'platform'`으로 바꾸려 하면 수정한 행이 뷰 조건을 벗어나므로 `WITH CHECK OPTION`이 거절한다. MySQL 8.4에서는 집계 뷰를 수정할 수 없다. `INFORMATION_SCHEMA.VIEWS`의 `IS_UPDATABLE`로 수정 가능 여부를 확인한다. 삽입에는 필수 열과 기본값 등 별도 조건도 적용된다.

**공식 문서** [ALTER VIEW](https://dev.mysql.com/doc/refman/8.4/en/alter-view.html) · [수정·삽입 가능한 뷰](https://dev.mysql.com/doc/refman/8.4/en/view-updatability.html) · [WITH CHECK OPTION](https://dev.mysql.com/doc/refman/8.4/en/view-check-option.html)

## 3. 접근 권한과 실행 계획 확인하기

- 원본의 `hourly_rate`를 명단에서 제외하고, 보고서 계정에 명단 뷰의 `SELECT` 권한을 부여한다. 조회자가 원본을 직접 읽을 수 있는지 기존 계정과 역할의 권한도 확인한다.
- MySQL 8.4의 기본값인 `SQL SECURITY DEFINER`는 원본 객체 접근을 뷰 정의자의 권한으로 확인한다. `SQL SECURITY INVOKER`는 호출자의 권한으로 확인한다. 뷰를 노출할 때는 어떤 계정의 권한으로 원본을 읽을지 함께 결정한다.
- 뷰는 쿼리를 재사용하는 수단이며 실행 비용은 정의와 바깥 조회 조건에 따라 달라진다. MySQL 8.4는 뷰 정의를 바깥 쿼리에 병합하거나, 중간 결과를 임시 테이블로 만들어 처리할 수 있다. 실제 조회 조건을 포함한 `EXPLAIN`으로 계획을 확인한다.

```sql
EXPLAIN
SELECT team_code, active_count
FROM lab07_team_activity
WHERE team_code = 'support';
```

**공식 문서** [뷰 권한과 SQL SECURITY](https://dev.mysql.com/doc/refman/8.4/en/create-view.html) · [GRANT](https://dev.mysql.com/doc/refman/8.4/en/grant.html) · [뷰 처리 알고리즘](https://dev.mysql.com/doc/refman/8.4/en/view-algorithms.html)

## 4. 실습 객체 정리하기

`DROP VIEW`로 두 뷰의 정의를 제거한 뒤 원본 테이블의 행 수를 확인한다. 마지막에 실습용 원본 테이블을 제거한다.

```sql
DROP VIEW lab07_active_directory, lab07_team_activity;

SELECT COUNT(*) AS remaining_agent_count
FROM lab07_agents;

DROP TABLE lab07_agents;
```

뷰를 지운 시점에는 원본의 3행을 조회할 수 있다.

**공식 문서** [DROP VIEW](https://dev.mysql.com/doc/refman/8.4/en/drop-view.html)
