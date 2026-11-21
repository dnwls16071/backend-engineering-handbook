# Recursive CTEs and Hierarchical Queries

폴더, 조직도, 카테고리처럼 각 행에 부모 ID가 있는 데이터는 `WITH RECURSIVE`로 지정한 노드부터 내려갈 수 있다. PostgreSQL 18 예제에서 깊이는 시작 노드를 기준으로 `0`부터 센다.

## 1. 시작 행에서 자식 행으로 확장하기

같은 세션에서 부모 ID와 형제 정렬 순서가 있는 폴더를 준비한다. `2`와 `3`에는 같은 정렬 순서를 부여한다.

```sql
CREATE TEMP TABLE folders (
    id integer PRIMARY KEY,
    parent_id integer REFERENCES folders (id),
    sibling_order integer NOT NULL,
    name text NOT NULL
);
INSERT INTO folders VALUES
    (1, NULL, 10, '문서'),
    (2, 1,    20, '기술'),
    (3, 1,    20, '운영'),
    (4, 2,    10, '데이터베이스'),
    (5, 1,    10, '온보딩');
CREATE INDEX ON folders (parent_id);
```

`UNION ALL` 앞은 시작 행을 고르는 앵커다. 뒤의 재귀 항은 직전 단계의 행을 `tree`로 받아 `parent_id`가 일치하는 자식을 찾는다. 새 행이 없으면 재귀가 끝난다. 자식 탐색을 반복할 때는 `parent_id`가 선두인 인덱스를 실행 계획에서 확인한다. [PostgreSQL 18 재귀 쿼리 평가](https://www.postgresql.org/docs/18/queries-with.html#QUERIES-WITH-RECURSIVE)

```sql
WITH RECURSIVE tree AS (
    SELECT id, parent_id, sibling_order, name, 0 AS depth
    FROM folders
    WHERE id = 1

    UNION ALL

    SELECT child.id, child.parent_id, child.sibling_order,
           child.name, tree.depth + 1
    FROM tree
    JOIN folders AS child ON child.parent_id = tree.id
)
SEARCH DEPTH FIRST BY sibling_order, id SET display_path
CYCLE id SET is_cycle USING visited_path
SELECT id, name, depth
FROM tree
WHERE NOT is_cycle
ORDER BY display_path;
```

## 2. 순환과 탐색 범위 제어하기

`CYCLE id`는 현재 경로에서 같은 ID를 다시 만나면 그 행에 `is_cycle`을 표시하고 해당 경로의 확장을 멈춘다. 위 쿼리에서 바깥 `WHERE`를 빼고 `is_cycle`과 `visited_path`를 출력하면 어느 경로에서 ID가 반복됐는지 확인할 수 있다. 테스트 데이터에서는 `UPDATE folders SET parent_id = 4 WHERE id = 1;`로 `1 → 2 → 4 → 1` 순환을 만들고, 확인 후 `UPDATE folders SET parent_id = NULL WHERE id = 1;`로 되돌린다.

`UNION`의 중복 판정에는 깊이를 포함한 결과 행 전체가 쓰인다. 같은 노드가 더 깊은 위치에 나타나면 행 값이 달라 순환이 계속될 수 있다. 화면에서 깊이 2까지 탐색할 때는 재귀 항에 `WHERE tree.depth < 2`를 추가한다. 이 조건은 깊이 2인 행을 출력하되 그 아래 자식으로의 확장을 막는다. [PostgreSQL 18 순환 감지](https://www.postgresql.org/docs/18/queries-with.html#QUERIES-WITH-CYCLE)

## 3. 탐색 결과와 형제 순서 정하기

`SEARCH DEPTH FIRST`는 정렬에 사용할 경로를 계산한다. 최종 `ORDER BY display_path`로 정렬하면 부모 다음에 해당 자식의 하위 트리를 출력하고, 형제 순서가 같으면 `id`로 순서를 확정한다. 예제의 ID 순서는 `1, 5, 2, 4, 3`이다. 같은 형제 순서를 유지하면서 깊이별로 묶으려면 `ORDER BY depth, display_path`를 사용한다. 이때 순서는 `1, 5, 2, 3, 4`다. [PostgreSQL 18 탐색 순서](https://www.postgresql.org/docs/18/queries-with.html#QUERIES-WITH-SEARCH)

SQL에서 시작 노드와 깊이를 제한하면 필요한 하위 트리만 전송할 수 있다. 화면에서 접고 펼치거나 여러 표시 순서를 지원한다면, 필요한 행을 한 번에 읽고 애플리케이션에서 `parent_id`별로 묶어 트리를 구성할 수 있다. 전송 행 수와 애플리케이션 메모리 사용량을 살피고, 노드마다 자식 조회를 실행할 경우 왕복 횟수도 확인한다.
