# JSON Data Modeling

JSON 열은 상품의 가변 규격, 사용자 설정, 이벤트 메타데이터처럼 구조가 달라질 수 있는 값을 한 문서로 저장한다. 식별자, 외래 키와 금액처럼 관계 제약이나 반복 집계가 필요한 데이터에는 명시적인 열을 두고, 나머지 속성은 읽기·쓰기 단위와 변경 주기를 보고 JSON에 넣을지 결정한다.

JSON 객체는 이름과 값의 쌍, 배열은 순서가 있는 값의 목록이다. 문자열, 수, 불리언, `null`과 중첩된 객체·배열을 사용할 수 있다. 예를 들어 같은 값처럼 보이는 문자열 `"42"`와 숫자 `42`는 구분해야 한다. JSON 자료형이 문법의 유효성을 검사하는 것과, 특정 키가 필수이며 값이 정해진 형식이라는 업무 규칙을 검사하는 것은 별개다. [MySQL JSON 자료형](https://dev.mysql.com/doc/refman/8.4/en/json.html) · [MySQL JSON 스키마 검증 함수](https://dev.mysql.com/doc/refman/8.4/en/json-validation-functions.html)

## 1. JSON 값 추출, 갱신, 행 변환 실습

실습 환경은 MySQL 8.4(InnoDB)다. 상품 속성에서 색상을 생성 열로 꺼내고, 옵션 배열은 재고 조회용 행으로 펼친다. 네 가지 입력을 사용하여 색상 문자열, JSON의 `null`, 누락된 색상 키, 컬럼 자체의 SQL `NULL`을 비교한다.

```sql
CREATE TABLE dd21_products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(80) NOT NULL,
    attributes JSON,
    color VARCHAR(24) GENERATED ALWAYS AS (
        CASE
            WHEN JSON_TYPE(JSON_EXTRACT(attributes, '$.color')) = 'STRING'
            THEN JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.color'))
        END
    ) VIRTUAL,
    CHECK (attributes IS NULL OR JSON_TYPE(attributes) = 'OBJECT'),
    INDEX idx_dd21_color (color)
) ENGINE = InnoDB;

INSERT INTO dd21_products (product_id, product_name, attributes) VALUES
    (101, 'Canvas Bag', JSON_OBJECT(
        'color', 'blue',
        'variants', JSON_ARRAY(
            JSON_OBJECT('size', 'S', 'stock', 3),
            JSON_OBJECT('size', 'M', 'stock', 0)
        )
    )),
    (102, 'Gift Bag', JSON_OBJECT('color', NULL)),
    (103, 'Cable Bag', JSON_OBJECT()),
    (104, 'Travel Bag', NULL);

SELECT product_id,
       CASE
           WHEN attributes IS NULL THEN 'SQL NULL'
           WHEN JSON_CONTAINS_PATH(attributes, 'one', '$.color') = 0 THEN 'MISSING'
           WHEN JSON_TYPE(JSON_EXTRACT(attributes, '$.color')) = 'NULL' THEN 'JSON null'
           ELSE 'VALUE'
       END AS color_state
FROM dd21_products
ORDER BY product_id;

UPDATE dd21_products
SET attributes = JSON_SET(attributes, '$.color', 'navy')
WHERE product_id = 101;

SELECT product_id, color
FROM dd21_products
WHERE color = 'navy';

SELECT p.product_id, v.size_code, v.stock
FROM dd21_products AS p
JOIN JSON_TABLE(
    COALESCE(p.attributes, JSON_OBJECT()),
    '$.variants[*]' COLUMNS (
        ordinal FOR ORDINALITY,
        size_code VARCHAR(16) PATH '$.size' ERROR ON EMPTY ERROR ON ERROR,
        stock INT PATH '$.stock' ERROR ON EMPTY ERROR ON ERROR
    )
) AS v ON TRUE
WHERE p.product_id = 101
ORDER BY v.ordinal;
```

첫 조회에서 101은 `VALUE`, 102는 `JSON null`, 103은 `MISSING`, 104는 `SQL NULL`이다. 갱신 후 색상으로 검색하면 101만 `navy`로 나온다. 배열 조회는 101의 옵션 `S, 3`과 `M, 0`을 차례로 반환한다. `JSON_SET`은 경로에 따라 값을 추가하거나 교체하고, `JSON_REMOVE`는 키를 없앤다. `JSON_TABLE`은 경로에 저장된 JSON `null`을 SQL `NULL`로 변환하므로, 값이 없을 때의 규칙을 점검하려면 경로 존재 여부도 검사한다. [MySQL JSON 검색 함수](https://dev.mysql.com/doc/refman/8.4/en/json-search-functions.html) · [문서 변경 함수](https://dev.mysql.com/doc/refman/8.4/en/json-modification-functions.html) · [JSON_TABLE](https://dev.mysql.com/doc/refman/8.4/en/json-table-functions.html)

## 2. 조회 경로와 유일성 제약 결정하기

| 쿼리 패턴 | MySQL 8.4에서 가능한 구현 |
| --- | --- |
| 단일 경로의 값으로 검색 | 값의 유형과 길이를 정한 생성 열에 B-tree 인덱스를 만들거나, 적합한 스칼라 표현식으로 함수 인덱스를 만든다. |
| JSON 배열의 원소로 포함 여부 검색 | InnoDB의 멀티 밸류 인덱스를 검토한다. 사용 가능한 조건에는 `MEMBER OF`, `JSON_CONTAINS`, `JSON_OVERLAPS`가 있으며 인덱스 정의와 비교 값의 자료형을 맞춘다. |
| 자주 조인하고 개별 요소를 갱신하거나 검증 | 배열 요소를 자식 테이블로 두고 외래 키와 행 수준 제약을 적용한다. |

MySQL에서 예제의 생성 열은 색상 값이 문자열일 때만 인덱스에 사용할 스칼라 값을 만든다. 문서에 값이 없거나 JSON `null`일 때 생성 열 값은 SQL `NULL`이다. 이 생성 열에 `UNIQUE`가 있다면 추출된 문자열의 중복은 거부하지만 여러 SQL `NULL`은 허용한다. 색상이 필수인 경우 키의 존재와 자료형도 검사한다. 인덱스가 어느 행에 실제로 만들어지는지를 정하는 부분 인덱스는 PostgreSQL처럼 지원하는 DBMS에서 별도의 조건으로 정의할 수 있다. [MySQL 생성 열](https://dev.mysql.com/doc/refman/8.4/en/create-table-generated-columns.html) · [MySQL 고유·함수·멀티 밸류 인덱스](https://dev.mysql.com/doc/refman/8.4/en/create-index.html) · [PostgreSQL 부분 인덱스](https://www.postgresql.org/docs/current/indexes-partial.html)

## 3. 관계형 열, EAV, JSON의 적용 범위

업무 규칙이 안정적이고 외래 키나 개별 값의 유일성이 필요하면 관계형 열과 테이블로 표현한다. 운영자가 속성 정의를 등록하고, 값 행을 별도로 관리해야 하면 [EAV](20_entity_attribute_value_modeling.md)를 후보로 본다. 엔티티별 설정이나 가변 메타데이터를 한 번에 읽고 쓴다면 JSON을 검토한다. 이벤트 데이터를 JSON으로 저장하더라도 발생 시각과 이벤트 종류처럼 공통 필터에 쓰는 값은 일반 열에 둘 수 있다.

문서형 데이터베이스를 선택할 때도 문서의 경계와 함께 읽는 관계, 쓰기 원자성의 범위, 조회 분포를 검토한다. 인덱스, 트랜잭션, 분산 동작의 특성은 제품의 지원 범위와 운영 방식에 따라 달라진다. [MongoDB 데이터 모델링의 문서와 관계](https://www.mongodb.com/docs/manual/data-modeling/)
