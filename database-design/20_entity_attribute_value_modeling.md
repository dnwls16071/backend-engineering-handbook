# Entity-Attribute-Value Modeling

EAV는 가변 속성을 엔티티와 속성 정의를 참조하는 값 행으로 저장하는 모델이다. 상품명과 같은 공통 정보는 상품 테이블에 두고, 진열 카테고리마다 달라지는 규격은 필요한 상품에만 값 행을 추가할 수 있다. [Dinu와 Nadkarni의 EAV 모델링 지침](https://pmc.ncbi.nlm.nih.gov/articles/PMC2110957/)

| 구성 | 담을 내용 |
| --- | --- |
| Entity | 상품 ID, 상품명, 카테고리처럼 엔티티 자체의 정보 |
| Attribute | 속성의 이름, 단위, 값의 종류, 적용 대상, 입력 규칙 |
| Value | 특정 상품에 부여한 특정 속성의 값 |

속성명과 값을 모두 문자열로 저장하면 이름 변경이 어렵고 숫자 비교나 정렬도 문자열 규칙을 따른다. 속성 정의에는 안정적인 식별자를 부여하고, 숫자와 문자열은 해당 자료형의 열에 저장한다. 속성이 늘어날 때마다 테이블 변경 없이 정의 행을 추가할 수 있지만, 새 자료형이나 새로운 검증 규칙을 도입하면 스키마 또는 쓰기 코드가 달라질 수 있다.

## 1. 속성 정의와 값의 종류 검증하기

실습 환경은 MySQL 8.4(InnoDB)다. 상품은 속성당 값 하나를 가지며, 속성은 카테고리 하나에만 속한다. 값 테이블의 복합 외래 키는 상품과 속성 정의의 카테고리가 같은지, 정의에 저장한 값의 종류가 일치하는지 검사한다. `CHECK`는 값 행에서 그 종류에 해당하는 열만 채우도록 제한한다. [MySQL 복합 외래 키 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html) · [MySQL 행 단위 CHECK 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html)

```sql
CREATE TABLE dd20_products (
    product_id BIGINT PRIMARY KEY,
    category_code VARCHAR(12) NOT NULL,
    product_name VARCHAR(80) NOT NULL,
    UNIQUE (product_id, category_code)
) ENGINE = InnoDB;

CREATE TABLE dd20_attribute_definitions (
    attribute_id BIGINT PRIMARY KEY,
    category_code VARCHAR(12) NOT NULL,
    attribute_code VARCHAR(24) NOT NULL,
    value_kind VARCHAR(8) NOT NULL,
    CHECK (value_kind IN ('NUMBER', 'TEXT')),
    UNIQUE (category_code, attribute_code),
    UNIQUE (attribute_id, category_code, value_kind)
) ENGINE = InnoDB;

CREATE TABLE dd20_attribute_values (
    product_id BIGINT NOT NULL,
    attribute_id BIGINT NOT NULL,
    category_code VARCHAR(12) NOT NULL,
    value_kind VARCHAR(8) NOT NULL,
    number_value DECIMAL(8, 2),
    text_value VARCHAR(100),
    PRIMARY KEY (product_id, attribute_id),
    CHECK (
        (value_kind = 'NUMBER' AND number_value IS NOT NULL AND text_value IS NULL)
        OR (value_kind = 'TEXT' AND text_value IS NOT NULL AND number_value IS NULL)
    ),
    FOREIGN KEY (product_id, category_code)
        REFERENCES dd20_products (product_id, category_code),
    FOREIGN KEY (attribute_id, category_code, value_kind)
        REFERENCES dd20_attribute_definitions (attribute_id, category_code, value_kind),
    INDEX idx_dd20_number_lookup (attribute_id, number_value, product_id)
) ENGINE = InnoDB;

INSERT INTO dd20_products VALUES
    (101, 'CABINET', 'Low Cabinet'),
    (102, 'CABINET', 'Tall Cabinet');
INSERT INTO dd20_attribute_definitions VALUES
    (1, 'CABINET', 'width_cm', 'NUMBER'),
    (2, 'CABINET', 'finish', 'TEXT');
INSERT INTO dd20_attribute_values VALUES
    (101, 1, 'CABINET', 'NUMBER', 72.50, NULL),
    (101, 2, 'CABINET', 'TEXT', NULL, 'oak'),
    (102, 1, 'CABINET', 'NUMBER', 85.00, NULL),
    (102, 2, 'CABINET', 'TEXT', NULL, 'white');

SELECT a.attribute_code, v.number_value, v.text_value
FROM dd20_attribute_values AS v
JOIN dd20_attribute_definitions AS a ON a.attribute_id = v.attribute_id
WHERE v.product_id = 101
ORDER BY a.attribute_id;

SELECT p.product_id, p.product_name
FROM dd20_products AS p
JOIN dd20_attribute_values AS w ON w.product_id = p.product_id
JOIN dd20_attribute_values AS f ON f.product_id = p.product_id
WHERE w.attribute_id = 1 AND w.number_value >= 70
  AND f.attribute_id = 2 AND f.text_value = 'oak'
ORDER BY p.product_id;
```

첫 조회는 101의 너비 72.50과 마감 `oak`를 두 행으로 반환한다. 두 가지 속성 조건을 함께 검색하면 상품 101만 나온다. 숫자 검색은 속성 식별자와 숫자 값으로 범위를 좁히는 복합 인덱스를 후보로 삼을 수 있다. [MySQL 복합 인덱스](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html)

## 2. 제약이 보장하는 경계 확인하기

- 복합 외래 키와 `CHECK`는 존재하는 값 행의 종류와 범위를 검증하는 데 쓸 수 있다. 상품을 게시할 때 필요한 속성 값이 모두 존재하는지는 별도의 쓰기 규칙으로 확인한다. MySQL의 `CHECK`에는 다른 테이블의 열이나 서브쿼리를 넣을 수 없다. [MySQL CHECK 제약의 표현식 범위](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html)
- 속성별 고정 선택지를 강제하려면 가능한 값의 목록을 관계로 두고 그 값을 참조하도록 정의할 수 있다. 값 여러 개가 필요한 속성은 중복 판단 기준과 순서를 정한 뒤 키에 선택지 ID 또는 순번을 포함한다.
- 속성을 여러 개 조합하면 같은 값 테이블을 여러 번 조인하거나 값을 그룹화해야 한다. 안정적인 핵심 값과 필터가 많은 속성은 전용 열이나 테이블로 두고, 동적으로 추가해야 할 희소 속성에 EAV를 적용할지 검토한다. 엔티티별 속성을 한 번에 읽는 비중이 높다면 [JSON 모델](21_json_data_modeling.md)과 비교한다.
