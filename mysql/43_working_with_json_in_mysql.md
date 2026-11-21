# Working with JSON in MySQL

MySQL 8.4의 `JSON` 열은 저장할 때 문법을 검사하고, 경로로 내부 값을 읽기 좋은 바이너리 형식으로 저장한다. 필수 키의 존재나 값의 업무 규칙은 별도로 검증한다. 예를 들어 `{"priority":"high"}`도 유효한 JSON이므로, 우선순위를 정수로 관리하려면 쓰기 경로에 검증이 필요하다. [MySQL JSON 데이터 타입](https://dev.mysql.com/doc/refman/8.4/en/json.html) · [MySQL JSON 스키마 검증](https://dev.mysql.com/doc/refman/8.4/en/json-validation-functions.html)

## 값을 꺼내고 세 가지 상태를 구분한다

```sql
CREATE TABLE event_payloads (
    event_id BIGINT PRIMARY KEY,
    payload JSON
) ENGINE = InnoDB;

INSERT INTO event_payloads VALUES
    (1, NULL), (2, '{}'), (3, '{"priority":null}'),
    (4, '{"priority":3,"tag_ids":[7,12]}');

SELECT event_id, payload IS NULL AS doc_is_null,
       JSON_CONTAINS_PATH(payload, 'one', '$.priority') AS has_priority,
       JSON_TYPE(payload->'$.priority') AS priority_type,
       JSON_VALUE(payload, '$.priority' RETURNING UNSIGNED) AS priority
FROM event_payloads ORDER BY event_id;
```

1번은 문서가 SQL `NULL`이고 `has_priority`도 SQL `NULL`이다. 2번은 경로가 없어 `has_priority`가 `0`이다. 3번은 경로가 있으므로 `has_priority`가 `1`이고 `JSON_TYPE()`은 문자열 `'NULL'`을 반환한다. 기본 설정의 `JSON_VALUE()`는 세 경우 모두 SQL `NULL`을 반환한다. `->`는 JSON 값을 추출하고 `->>`는 추출한 값의 따옴표를 벗긴다. 숫자로 비교하려면 `JSON_VALUE()`에 반환 타입을 지정한다. [MySQL JSON 검색 함수](https://dev.mysql.com/doc/refman/8.4/en/json-search-functions.html) · [MySQL JSON 속성 함수](https://dev.mysql.com/doc/refman/8.4/en/json-attribute-functions.html)

## 검색 조건에 맞게 인덱스를 만든다

```sql
CREATE INDEX ix_priority ON event_payloads
    ((JSON_VALUE(payload, '$.priority' RETURNING UNSIGNED)));
CREATE INDEX ix_tag_ids ON event_payloads
    ((CAST(payload->'$.tag_ids' AS UNSIGNED ARRAY)));

EXPLAIN SELECT event_id FROM event_payloads
WHERE JSON_VALUE(payload, '$.priority' RETURNING UNSIGNED) = 3;
EXPLAIN SELECT event_id FROM event_payloads
WHERE 7 MEMBER OF (payload->'$.tag_ids');
```

- 스칼라 경로는 `JSON_VALUE()` 표현식이나 타입이 정해진 생성 열에 인덱스를 건다. 표현식 인덱스를 사용할 쿼리는 경로와 반환 타입을 인덱스 정의와 맞춘다. 변환 실패나 경로 누락을 구분해야 하면 `ON ERROR`와 `ON EMPTY` 동작도 정한다. 데이터 분포에 따른 인덱스 사용 여부는 `EXPLAIN`에서 확인한다. [MySQL JSON 검색 함수](https://dev.mysql.com/doc/refman/8.4/en/json-search-functions.html) · [MySQL 생성 열 인덱스 최적화](https://dev.mysql.com/doc/refman/8.4/en/generated-column-index-optimizations.html)
- InnoDB 다중 값 인덱스는 배열 원소를 검색하는 `MEMBER OF()`, `JSON_CONTAINS()`, `JSON_OVERLAPS()`에 쓸 수 있다. 빈 배열은 인덱스 엔트리를 만들지 않으며 인덱싱하는 배열에 JSON `null` 원소가 있으면 오류가 난다. 정렬과 커버링 인덱스에는 쓸 수 없고 기존 테이블에 추가할 때는 테이블 복사가 필요하다. [MySQL 다중 값 인덱스](https://dev.mysql.com/doc/refman/8.4/en/create-index.html)
