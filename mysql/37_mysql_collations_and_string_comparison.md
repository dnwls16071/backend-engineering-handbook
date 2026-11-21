# MySQL Collations and String Comparison

문자 집합은 문자를 표현하는 방법을, 콜레이션은 문자열의 동등 여부와 정렬 순서를 정한다. 같은 `utf8mb4`라도 `utf8mb4_0900_ai_ci`는 악센트와 대소문자를 구분하지 않고, `utf8mb4_0900_as_cs`는 둘 다 구분한다. 이 차이는 `WHERE`와 조인뿐 아니라 `ORDER BY`, `GROUP BY`, `UNIQUE` 인덱스에도 영향을 준다. [MySQL 콜레이션 이름](https://dev.mysql.com/doc/refman/8.4/en/charset-collation-names.html) · [MySQL 유일 인덱스](https://dev.mysql.com/doc/refman/8.4/en/create-index.html#unique-indexes)

## 기본값과 표현식의 우선순위

MySQL 8.4의 서버 기본값은 `utf8mb4`와 `utf8mb4_0900_ai_ci`다. 별도 지정 없이 만들면 데이터베이스는 서버, 테이블은 데이터베이스, 문자열 컬럼은 테이블의 기본값을 따른다. 실제 컬럼 설정은 `SHOW FULL COLUMNS`로 확인한다. 테이블 기본값만 바꾸는 `ALTER TABLE ... DEFAULT CHARACTER SET`은 이후 정의하는 컬럼에 적용된다. [MySQL 서버 기본값](https://dev.mysql.com/doc/refman/8.4/en/charset-server.html) · [MySQL 컬럼 콜레이션](https://dev.mysql.com/doc/refman/8.4/en/charset-column.html) · [MySQL ALTER TABLE](https://dev.mysql.com/doc/refman/8.4/en/alter-table.html#alter-table-character-set)

문자열 리터럴의 기본 콜레이션은 `collation_connection`의 영향을 받는다. 표현식에서는 강제성(coercibility) 값이 작은 쪽이 우선이어서 명시적 `COLLATE`(0), 컬럼(2), 리터럴(4) 순으로 적용된다. 우선순위가 같은 서로 다른 콜레이션은 문자 집합과 콜레이션 조합에 따라 하나를 선택하거나 `Illegal mix of collations` 오류를 낸다. 문자열 컬럼에 변환이나 다른 `COLLATE`를 적용하면 기존 인덱스로 탐색하지 못할 수 있으므로, 자주 비교하는 컬럼의 문자 집합과 콜레이션을 맞추고 `EXPLAIN`으로 확인한다. [MySQL 연결 콜레이션](https://dev.mysql.com/doc/refman/8.4/en/charset-connection.html) · [MySQL 콜레이션 강제성](https://dev.mysql.com/doc/refman/8.4/en/charset-collation-coercibility.html) · [MySQL의 인덱스 사용](https://dev.mysql.com/doc/refman/8.4/en/mysql-indexes.html)

## 콜레이션을 바꾸기 전에 중복을 확인한다

`Cafe`와 `café`는 `utf8mb4_0900_as_cs`에서 서로 다른 값으로 저장된다. `utf8mb4_0900_ai_ci`에서는 같게 비교되므로 `GROUP BY`에 대상 콜레이션을 지정하면 전환 후 `UNIQUE` 키가 충돌할 그룹을 미리 찾을 수 있다.

```sql
CREATE TABLE accounts_collation_demo (
    account_id BIGINT PRIMARY KEY,
    handle VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL,
    UNIQUE KEY ux_handle (handle)
) ENGINE = InnoDB;

SHOW FULL COLUMNS FROM accounts_collation_demo;
INSERT INTO accounts_collation_demo VALUES (1, 'Cafe'), (2, _utf8mb4 X'636166C3A9');

SELECT handle COLLATE utf8mb4_0900_ai_ci AS target_handle, COUNT(*) AS matches
FROM accounts_collation_demo
GROUP BY target_handle
HAVING COUNT(*) > 1;
```

새 규칙에서 같은 키가 둘 이상 남아 있으면 `UNIQUE` 제약을 유지한 전환은 중복 키 오류로 실패한다. 실제 전환에서는 각 유일 키의 구성에 맞춰 충돌을 확인하고 데이터 처리 기준을 정한 뒤 컬럼을 변경한다. `ALTER TABLE ... MODIFY`는 컬럼 단위로, `ALTER TABLE ... CONVERT TO CHARACTER SET ... COLLATE ...`는 테이블의 문자 컬럼 전체에 적용한다. 변경 후에는 조인과 정렬의 결과, 인덱스 접근 유형을 다시 확인한다. 뒤 공백의 비교 방식은 콜레이션의 `PAD SPACE`와 `NO PAD` 속성을 확인한다. [MySQL ALTER TABLE](https://dev.mysql.com/doc/refman/8.4/en/alter-table.html#alter-table-character-set) · [CHAR and VARCHAR Storage and Comparison](25_char_and_varchar_storage_and_comparison.md)
