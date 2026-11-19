# SQL Antipatterns and Query Refactoring

쿼리를 리팩터링할 때는 결과의 행 수, 중복, NULL 처리, 출력 열이 그대로인지 먼저 확인한다. 이후 같은 데이터와 바인딩 값에서 실행 계획과 작업량을 비교한다. 실습 환경은 MySQL 8.4(InnoDB)이며 [18번의 모의 데이터](18_mysql_dml_fundamentals_and_advanced_query_patterns.md)를 사용한다.

## 1. 반복되는 CASE 매핑 · 차원 테이블과 뷰

조건부 집계나 한 화면에서만 쓰는 분류에는 CASE가 자연스럽다. 여러 조회가 상태 코드를 같은 이름과 정렬 순서로 매핑한다면 차원 테이블에 코드, 표시명, 표시 순서를 관리할 수 있다. 코드에 대한 행이 유일해야 조인 후 원래 행 수를 유지할 수 있다.

```sql
CREATE TEMPORARY TABLE mysql_lab_state_dim (
    state_code VARCHAR(12) PRIMARY KEY,
    display_name VARCHAR(30) NOT NULL,
    display_order INT NOT NULL
);

INSERT INTO mysql_lab_state_dim VALUES
    ('OPEN', 'Open', 1), ('DONE', 'Done', 2), ('CANCELLED', 'Cancelled', 3);

SELECT t.task_id, t.title, COALESCE(d.display_name, 'Unknown') AS state_name
FROM mysql_lab_tasks AS t
LEFT JOIN mysql_lab_state_dim AS d ON d.state_code = t.task_state
ORDER BY t.task_id;
```

위 예시는 정의되지 않은 코드도 결과에 남긴다. 공통 조회 계약이 필요하면 영구 차원 테이블을 참조하는 뷰로 노출하고 소비자가 쓰는 열을 명시한다. [Reference Data and Code Tables](../database-design/13_reference_data_and_code_tables.md) · [CREATE VIEW Statement](https://dev.mysql.com/doc/refman/8.4/en/create-view.html)

## 2. 인덱스 열에 함수 적용 · 원본 값의 범위로 변경

`DATE(created_at) = '2025-03-01'`처럼 인덱스 열에 함수를 적용하면 해당 원본 키의 범위를 바로 찾기 어려울 수 있다. 같은 날짜를 원본 시간의 반개방 구간으로 표현하고 두 계획을 비교한다. 시간대 변환이 필요한 경우에는 경계 시각을 저장 기준에 맞춰 먼저 계산한다. 표현식 자체로 반복 검색해야 한다면 MySQL 함수 인덱스 또는 인덱싱한 생성 열을 검토한다. [Range Optimization](https://dev.mysql.com/doc/refman/8.4/en/range-optimization.html) · [Generated Column Index Optimization](https://dev.mysql.com/doc/refman/8.4/en/generated-column-index-optimizations.html)

```sql
EXPLAIN FORMAT=TREE
SELECT task_id FROM mysql_lab_tasks WHERE DATE(created_at) = '2025-03-01';

EXPLAIN FORMAT=TREE
SELECT task_id FROM mysql_lab_tasks
WHERE created_at >= '2025-03-01' AND created_at < '2025-03-02';
```

## 3. 뷰의 SELECT * · 필요한 열을 계약으로 명시

MySQL은 뷰 정의를 생성 시점에 고정한다. `SELECT *`로 만들었어도 원본 테이블에 새 열을 추가했을 때 기존 뷰에 새 열이 자동으로 추가되지 않는다. 뷰가 이름이나 내용이 바뀔 수 있는 열을 넓게 참조하면 변경의 영향을 받는 소비자가 늘어난다. 업무에 필요한 열과 별칭을 명시하면 뷰가 제공하는 결과가 분명해진다. [CREATE VIEW Statement](https://dev.mysql.com/doc/refman/8.4/en/create-view.html)

```sql
CREATE VIEW mysql_lab_open_task_list AS
SELECT task_id, project_id, title, created_at
FROM mysql_lab_tasks
WHERE task_state = 'OPEN';
```

## 4. DISTINCT 남용 · 중복의 원인부터 확인

태그가 있는 작업을 찾으려고 작업과 태그를 조인하면 태그 수만큼 작업 행이 늘어난다. 태그를 출력하지 않고 존재만 확인할 경우에는 `EXISTS`가 의도를 나타낸다. 조인 결과 중 실제로 중복된 값의 집합이 필요한 경우에는 `DISTINCT`를 사용한다. [Semijoin Transformations](https://dev.mysql.com/doc/refman/8.4/en/semijoins-antijoins.html)

```sql
SELECT t.task_id, t.title
FROM mysql_lab_tasks AS t
WHERE EXISTS (
    SELECT 1 FROM mysql_lab_task_labels AS l
    WHERE l.task_id = t.task_id AND l.label LIKE 'ops%'
)
ORDER BY t.task_id;
```

모의 데이터에서 101번 작업의 태그 두 개가 조건을 만족해도 작업은 한 번 반환된다.

## 5. 뷰 계층 과다 · 병합과 구체화 확인

여러 뷰를 겹친 경우 각 층의 필터, 조인, 집계가 최종 계획에서 어디에 배치되는지 확인한다. MySQL은 병합이 가능한 뷰의 정의를 바깥 쿼리와 합칠 수 있다. `GROUP BY`, `DISTINCT`, `LIMIT` 같은 요소는 병합을 제한할 수 있고, 필요한 경우 내부 임시 테이블에 중간 결과를 만든다. 계층을 줄일 때는 권한 경계나 공통 집계 계약을 제공하는지도 고려한다. [View Processing Algorithms](https://dev.mysql.com/doc/refman/8.4/en/view-algorithms.html) · [Derived Table, View, and CTE Optimization](https://dev.mysql.com/doc/refman/8.4/en/derived-table-optimization.html)
