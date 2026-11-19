# Subqueries and Derived Tables

서브쿼리의 반환 형태에 맞는 연산자를 고르고, 존재 확인·상관 계산·중간 집계에 사용하는 방법을 정리한다. 실습 환경은 MySQL 8.4다. 실습 데이터베이스를 선택한 뒤 같은 세션에서 SQL 블록을 위에서부터 실행한다.

## 1. 반환 형태와 사용 위치

| 반환 형태 | 대표 사용법 |
| --- | --- |
| 열 하나, 최대 한 행 | `WHERE`의 단일 값 비교 또는 `SELECT`의 한 열 |
| 열 하나, 여러 행 가능 | `IN`, `ANY`, `ALL`로 후보 값과 비교 |
| 열 여러 개, 최대 한 행 | `(a, b) = (SELECT x, y ...)`로 한 행의 열을 비교 |
| 열 여러 개, 여러 행 가능 | `(a, b) IN (SELECT x, y ...)`로 같은 조합이 있는지 확인 |
| 행의 존재 여부 | `EXISTS`와 `NOT EXISTS` |
| 테이블 형태 | `FROM (SELECT ...) AS alias`로 중간 결과를 조회 |

스칼라 서브쿼리는 한 열의 값을 사용한다. 0행이면 `NULL`, 두 행 이상이면 오류가 발생한다. 행 비교에서는 양쪽 열 수를 맞춘다. [MySQL 서브쿼리](https://dev.mysql.com/doc/refman/8.4/en/subqueries.html) · [스칼라 서브쿼리](https://dev.mysql.com/doc/refman/8.4/en/scalar-subqueries.html) · [행 서브쿼리](https://dev.mysql.com/doc/refman/8.4/en/row-subqueries.html)

```sql
CREATE TEMPORARY TABLE lab04_courses (
    course_id INT PRIMARY KEY,
    duration_min INT NOT NULL
);

CREATE TEMPORARY TABLE lab04_attempts (
    attempt_id INT PRIMARY KEY,
    course_id INT NOT NULL,
    member_id INT NOT NULL,
    finished BOOLEAN NOT NULL,
    spent_min INT NOT NULL
);

CREATE TEMPORARY TABLE lab04_reviews (
    course_id INT NOT NULL,
    member_id INT NOT NULL,
    PRIMARY KEY (course_id, member_id)
);

INSERT INTO lab04_courses VALUES (101, 45), (102, 60), (201, 50), (202, 75);
INSERT INTO lab04_attempts VALUES
    (1, 101, 11, TRUE, 38), (2, 101, 12, TRUE, 46),
    (3, 102, 11, TRUE, 55), (4, 201, 13, FALSE, 20),
    (5, 102, 13, FALSE, 30);
INSERT INTO lab04_reviews VALUES (101, 11), (102, 13);
```

## 2. 단일 값, 여러 값, 열의 조합 비교하기

```sql
SELECT c.course_id
FROM lab04_courses AS c
WHERE c.duration_min > (
    SELECT MAX(a.spent_min) FROM lab04_attempts AS a WHERE a.finished = TRUE
)
ORDER BY c.course_id;

SELECT c.course_id
FROM lab04_courses AS c
WHERE c.course_id IN (
    SELECT a.course_id FROM lab04_attempts AS a WHERE a.finished = TRUE
)
ORDER BY c.course_id;

SELECT a.attempt_id
FROM lab04_attempts AS a
WHERE (a.course_id, a.member_id) IN (
    SELECT r.course_id, r.member_id FROM lab04_reviews AS r
)
ORDER BY a.attempt_id;

SELECT 50 > ANY (
    SELECT a.spent_min FROM lab04_attempts AS a WHERE a.finished = TRUE
) AS greater_than_any;

SELECT 50 > ALL (
    SELECT a.spent_min FROM lab04_attempts AS a WHERE a.finished = TRUE
) AS greater_than_all;
```

첫 조회는 완료까지 걸린 최장 시간 `55`분보다 예정 시간이 긴 과정 `102`와 `202`를 반환한다. 두 번째 조회의 결과는 완료 기록이 있는 과정 `101`과 `102`다. 세 번째 조회는 두 열이 **같은 행의 조합**으로 일치하는 시도 `1`과 `5`를 찾는다.

`x > ANY (...)`는 후보 중 하나라도 `x`보다 작으면 참이고, `x > ALL (...)`는 모든 후보가 `x`보다 작을 때 참이다. 예제의 후보는 `38`, `46`, `55`다. MySQL 8.4에서 `50 > ANY (...)`의 참은 `1`, `50 > ALL (...)`의 거짓은 `0`으로 표시된다. 후보가 비어 있으면 `ANY`는 거짓, `ALL`은 참이다. `MIN`과 `MAX`로 바꿔 쓰면 빈 결과와 `NULL`에서 의미가 달라질 수 있으므로, 후보 집합의 조건을 확인한다. [MySQL ANY, IN, SOME](https://dev.mysql.com/doc/refman/8.4/en/any-in-some-subqueries.html) · [MySQL ALL](https://dev.mysql.com/doc/refman/8.4/en/all-subqueries.html)

## 3. 상관 서브쿼리로 존재 여부와 계산값 구하기

상관 서브쿼리는 내부에서 외부 쿼리의 열을 참조한다. 아래 예제는 외부의 `c.course_id`를 사용해 과정별 완료 기록의 존재 여부와 개수를 구한다. `EXISTS`는 결과 행이 하나라도 있으면 참이고, `NOT EXISTS`는 결과 행이 0개일 때 참이다. [MySQL 상관 서브쿼리](https://dev.mysql.com/doc/refman/8.4/en/correlated-subqueries.html) · [MySQL EXISTS와 NOT EXISTS](https://dev.mysql.com/doc/refman/8.4/en/exists-and-not-exists-subqueries.html)

```sql
SELECT c.course_id
FROM lab04_courses AS c
WHERE NOT EXISTS (
    SELECT 1
    FROM lab04_attempts AS a
    WHERE a.course_id = c.course_id AND a.finished = TRUE
)
ORDER BY c.course_id;

SELECT c.course_id,
       (SELECT COUNT(*)
        FROM lab04_attempts AS a
        WHERE a.course_id = c.course_id AND a.finished = TRUE) AS finish_count
FROM lab04_courses AS c
ORDER BY c.course_id;

SELECT 101 NOT IN (102, NULL) AS unknown_result;
```

첫 결과는 완료 기록이 없는 `201`과 `202`다. 두 번째는 과정별 완료 횟수 `2, 1, 0, 0`을 반환한다. 마지막 표현식은 `NULL`을 반환한다. `NOT IN`의 후보에 `NULL`이 섞이면 일치하는 후보가 없는 값도 비교 결과가 `UNKNOWN`이 될 수 있다. 미매칭을 검사할 때 비교 열이 `NULL`을 허용한다면, 원하는 결합 조건을 명시한 `NOT EXISTS`를 사용한다. [MySQL 비교 연산자와 NULL](https://dev.mysql.com/doc/refman/8.4/en/comparison-operators.html)

## 4. 파생 테이블에서 먼저 집계하기

`FROM`에 놓인 서브쿼리를 파생 테이블이라고 하며 별칭을 붙여 참조한다. 이 예제는 완료 기록을 과정별 한 행으로 먼저 집계한 후 과정에 붙인다. `COALESCE`로 미매칭 과정의 횟수를 `0`으로 바꾸면 앞의 상관 `COUNT(*)` 예제와 같은 값이 나온다. [MySQL 파생 테이블](https://dev.mysql.com/doc/refman/8.4/en/derived-tables.html)

```sql
SELECT c.course_id, COALESCE(t.finish_count, 0) AS finish_count
FROM lab04_courses AS c
LEFT JOIN (
    SELECT a.course_id, COUNT(*) AS finish_count
    FROM lab04_attempts AS a
    WHERE a.finished = TRUE
    GROUP BY a.course_id
) AS t ON t.course_id = c.course_id
ORDER BY c.course_id;
```

존재 여부를 확인할 때는 `EXISTS`로 외부 행의 단위를 유지할 수 있다. 내부 기록까지 직접 `JOIN`해 조회하면 매칭된 기록 수만큼 행이 늘어날 수 있다. 실제 실행 전략은 DBMS의 옵티마이저와 버전, 데이터 분포에 따라 달라진다. MySQL 8.4는 조건을 충족하는 `IN`과 `EXISTS`를 세미 조인 등으로 변환할 수 있다. 성능을 비교할 때는 같은 데이터와 인덱스에서 `EXPLAIN`으로 실행 계획을 확인한다. [MySQL 세미 조인과 안티 조인 최적화](https://dev.mysql.com/doc/refman/8.4/en/semijoins-antijoins.html) · [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
