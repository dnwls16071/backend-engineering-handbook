# JSON Storage, Queries, and Indexes Across Databases

JSON은 장비 유형마다 달라지는 속성처럼 구조가 달라질 수 있는 데이터를 한 열에 담는다. 식별자나 조인 키처럼 제약을 자주 적용하는 값은 일반 열에 두고, JSON 안에서 자주 필터링하는 값은 실제 조회 조건에 맞춰 인덱싱한다. 예제는 `{"priority":3,"device_ids":[101,205]}` 형태의 경보 데이터를 쓴다.

| 엔진 | 예제의 저장 방식 | 단일 경로의 스칼라 검색 | 여러 키·배열 처리 |
| --- | --- | --- | --- |
| Oracle Database 19c | `VARCHAR2` + `IS JSON` | `JSON_VALUE` 함수 기반 인덱스 | JSON 검색 인덱스 |
| SQL Server 2022 | `nvarchar(max)` + `ISJSON` | `JSON_VALUE`를 쓰는 계산 열 인덱스 | `OPENJSON`으로 배열을 행으로 변환 |
| PostgreSQL 18 | `jsonb` | `->>` 추출 결과의 B-tree 표현식 인덱스 | `jsonb`의 GIN 인덱스 |
| MySQL 8.4 | `JSON` | 함수 인덱스 또는 생성 열 인덱스 | InnoDB 다중 값 인덱스 |

경로 검증과 타입 변환 규칙은 엔진마다 다르다. JSON 문법 검사는 `priority`가 반드시 존재하거나 정수임을 보장하지 않는다. 누락된 키·JSON `null`·SQL `NULL`을 구분해야 하는 조회는 스칼라 추출과 경로 존재 검사를 함께 사용한다. [Oracle 19c · JSON 저장](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/overview-of-storage-and-management-of-JSON-data.html) · [SQL Server · JSON 함수](https://learn.microsoft.com/en-us/sql/t-sql/functions/json-functions-transact-sql?view=sql-server-ver16) · [PostgreSQL 18 · JSON 연산자](https://www.postgresql.org/docs/18/functions-json.html) · [MySQL 8.4 · JSON 검색 함수](https://dev.mysql.com/doc/refman/8.4/en/json-search-functions.html)

## 1. Oracle Database 19c

작은 문서를 `VARCHAR2(4000 BYTE)`에 저장하고 `IS JSON`으로 형식을 검사한다. `NULL ON EMPTY`는 경로가 없으면 SQL `NULL`을 반환하게 하고, `ERROR ON ERROR`는 배열을 숫자로 읽는 것 같은 변환 오류를 드러낸다. 인덱스와 조회에서 경로 및 `RETURNING` 타입을 맞춘다. [Oracle 19c · JSON 인덱스](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/indexes-for-json-data.html)

```sql
CREATE TABLE oracle_alert (
    id NUMBER PRIMARY KEY,
    payload VARCHAR2(4000 BYTE) NOT NULL CHECK (payload IS JSON)
);
CREATE INDEX oracle_alert_priority_idx ON oracle_alert (
    JSON_VALUE(payload, '$.priority' RETURNING NUMBER ERROR ON ERROR NULL ON EMPTY)
);
SELECT id FROM oracle_alert
WHERE JSON_VALUE(payload, '$.priority' RETURNING NUMBER ERROR ON ERROR NULL ON EMPTY) >= 3;
```

**연습 1.** `oracle_alert`에 `{"priority":3}`, `{"priority":1}`, `{}`를 각각 ID 1, 2, 3으로 넣고 조회에서 ID 1만 반환되는지 확인한다. 이어서 `{"priority":[3]}`을 넣으면 `ERROR ON ERROR` 때문에 입력이 실패하는지 확인한다.

## 2. SQL Server 2022

`ISJSON(payload, OBJECT)`로 최상위 객체를 검증한다. `JSON_VALUE`로 추출한 텍스트를 정수로 변환한 계산 열을 인덱싱한다. `TRY_CONVERT`는 정수로 변환할 수 없는 텍스트를 `NULL`로 만든다. 아래 세션 옵션은 계산 열 인덱스를 생성하고 유지하는 연결에도 적용한다. [SQL Server · ISJSON](https://learn.microsoft.com/en-us/sql/t-sql/functions/isjson-transact-sql?view=sql-server-ver16) · [SQL Server · JSON 인덱싱](https://learn.microsoft.com/en-us/sql/relational-databases/json/index-json-data?view=sql-server-ver16) · [SQL Server · 계산 열 인덱스](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/indexes-on-computed-columns?view=sql-server-ver16)

```sql
SET ANSI_NULLS, ANSI_PADDING, ANSI_WARNINGS, ARITHABORT,
    CONCAT_NULL_YIELDS_NULL, QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;

CREATE TABLE dbo.sqlserver_alert (
    id int PRIMARY KEY,
    payload nvarchar(max) NOT NULL CHECK (ISJSON(payload, OBJECT) = 1),
    priority AS TRY_CONVERT(int, JSON_VALUE(payload, '$.priority'))
);
CREATE INDEX sqlserver_alert_priority_idx ON dbo.sqlserver_alert (priority);
SELECT id FROM dbo.sqlserver_alert WHERE priority >= 3;
```

**연습 2.** `dbo.sqlserver_alert`에 `N'{"priority":10}'`, `N'{"priority":2}'`, `N'{"priority":"미정"}'`을 각각 ID 1, 2, 3으로 넣는다. `priority`가 정수로 비교되어 ID 1만 반환되는지 확인하고, ID 3의 계산 열을 조회해 SQL `NULL`을 확인한다.

SQL Server 2025에서는 네이티브 `json` 타입과 `CREATE JSON INDEX`로 여러 경로의 검색을 지원한다. [SQL Server 2025 · JSON 데이터](https://learn.microsoft.com/en-us/sql/relational-databases/json/json-data-sql-server?view=sql-server-ver17) · [SQL Server 2025 · CREATE JSON INDEX](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-json-index-transact-sql?view=sql-server-ver17)

## 3. PostgreSQL 18

`json`은 입력 텍스트를 보존한다. `jsonb`는 분해된 형식으로 저장하며 객체의 공백과 키 순서를 보존하지 않고, 중복 키는 마지막 값을 남긴다. 기본 `jsonb_ops` GIN은 키 존재(`?`, `?|`, `?&`), 포함(`@>`), JSONPath 매치(`@?`, `@@`)를 지원한다. `jsonb_path_ops`는 `@>`, `@?`, `@@`를 지원하며, 그 조건이 주력인 경우 더 작고 선택적인 인덱스가 될 수 있다. 수치 범위 검색에는 추출값을 변환한 B-tree 표현식 인덱스를 사용한다. [PostgreSQL 18 · JSON 자료형과 인덱싱](https://www.postgresql.org/docs/18/datatype-json.html)

```sql
CREATE TABLE pg_alert (id bigint PRIMARY KEY, payload jsonb NOT NULL);
CREATE INDEX pg_alert_payload_idx ON pg_alert USING gin (payload); -- jsonb_ops
CREATE INDEX pg_alert_priority_idx ON pg_alert (((payload->>'priority')::integer));
INSERT INTO pg_alert VALUES (1, '{"priority":3,"device_ids":[101,205]}');

SELECT id FROM pg_alert WHERE payload ? 'priority';
SELECT id FROM pg_alert WHERE payload @> '{"device_ids":[101]}';
SELECT id FROM pg_alert WHERE (payload->>'priority')::integer >= 3;
```

마지막 인덱스는 `priority`가 존재할 때 정수로 변환할 수 있다는 쓰기 규약을 전제로 한다. 변환 오류가 가능한 원본을 다룰 때는 적재 과정에서 값을 검증한 뒤 인덱스를 적용한다. [PostgreSQL 18 · 표현식 인덱스](https://www.postgresql.org/docs/18/indexes-expressional.html)

## 4. MySQL 8.4

네이티브 `JSON`은 입력을 검증하고 내부 바이너리 형식으로 저장한다. 단일 경로에 반복 접근한다면 `JSON_VALUE`의 반환 타입을 지정한 함수 인덱스를 쓰거나, 추출 결과를 이름 있는 생성 열로 정의해 그 열을 인덱싱한다. InnoDB의 다중 값 인덱스는 지정 경로의 배열 원소를 인덱싱하며, 같은 경로의 `MEMBER OF`, `JSON_CONTAINS`, `JSON_OVERLAPS` 조건에 활용할 수 있다. [MySQL 8.4 · JSON 데이터 타입](https://dev.mysql.com/doc/refman/8.4/en/json.html) · [MySQL 8.4 · CREATE INDEX](https://dev.mysql.com/doc/refman/8.4/en/create-index.html) · [MySQL 8.4 · 생성 열 인덱스](https://dev.mysql.com/doc/refman/8.4/en/create-table-secondary-indexes.html)

```sql
CREATE TABLE mysql_alert (id bigint PRIMARY KEY, payload JSON NOT NULL) ENGINE=InnoDB;
CREATE INDEX mysql_alert_priority_idx
    ON mysql_alert ((JSON_VALUE(payload, '$.priority' RETURNING UNSIGNED)));
CREATE INDEX mysql_alert_device_idx
    ON mysql_alert ((CAST(payload->'$.device_ids' AS UNSIGNED ARRAY)));
INSERT INTO mysql_alert VALUES (1, '{"priority":3,"device_ids":[101,205]}');

SELECT id FROM mysql_alert WHERE JSON_VALUE(payload, '$.priority' RETURNING UNSIGNED) >= 3;
SELECT id FROM mysql_alert WHERE 101 MEMBER OF (payload->'$.device_ids');
```

스칼라 등가·범위 검색에는 타입을 맞춘 경로 인덱스를, 배열 멤버십에는 해당 연산을 지원하는 인덱스를 선택한다. 실제 분포와 충분한 행 수에서 실행 계획을 확인한다. 작은 테이블이나 대부분의 행을 읽는 쿼리는 인덱스가 있어도 전체 스캔을 선택할 수 있다. [PostgreSQL 18 · EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) · [MySQL 8.4 · EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)
