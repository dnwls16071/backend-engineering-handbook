# Relational Inheritance Mapping

슈퍼타입은 여러 유형이 공유하는 식별자와 속성을 담고, 서브타입은 유형별 속성을 담는다. 예를 들어 상품은 모두 상품 ID와 이름이 있지만, 디지털 상품에는 파일 크기가, 실물 상품에는 배송 무게가 필요하다. 물리 모델은 한 상품이 여러 유형에 동시에 속할 수 있는지, 모든 상품에 상세 유형이 필요한지, 주문 항목에서 어떤 식별자로 상품을 참조할지를 먼저 정한다.

## 1. 세 가지 저장 전략 비교하기

| 전략 | 저장 구조 | 주로 확인할 비용과 제약 |
| --- | --- | --- |
| 구현 클래스마다 테이블 | 디지털 상품과 실물 상품의 테이블에 공통 속성도 각각 둔다. | 유형 안에서 읽기와 필수값 검증이 쉽다. 전체 상품을 읽으려면 보통 `UNION ALL`이 필요하고, 테이블별 키만으로는 전체 상품에 걸친 유일성을 강제할 수 없다. |
| 단일 테이블 | 한 상품 테이블에 유형 구분 값과 각 유형의 상세 열을 함께 둔다. | 상품 전체를 한 테이블에서 참조하고 조회한다. 다른 유형에서 비어 있어야 하는 열에는 공통 `NOT NULL`을 쓰기 어려우므로 유형별 필수값과 금지값을 조건부 `CHECK`로 표현한다. |
| 조인 전략 | 상품 테이블에는 공통 속성을, 서브타입 테이블에는 전용 속성을 둔다. | 전체 상품 관계는 공통 테이블을 참조하며 상세 열마다 일반 제약을 적용할 수 있다. 서브타입 상세 조회에는 조인이 필요하고, 상품 등록은 여러 테이블의 변경으로 이루어진다. |

구현 클래스별 테이블에는 각 유형을 직접 참조하는 외래 키를 둘 수 있다. 주문 항목의 외래 키 하나로 여러 유형의 테이블 중 하나를 선택해 참조하려면 공통 상품 식별자를 별도로 두거나 참조 모델을 바꾸어야 한다. 주문·가격·재고처럼 전체 상품을 공통으로 참조하는 관계가 있는지, 조회가 유형별로 이루어지는지, 유형별 열과 제약이 얼마나 달라지는지 비교한다. [Jakarta Persistence 3.2의 세 가지 상속 매핑](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2#inheritance-mapping-strategies) · [MySQL 외래 키 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)

## 2. 조인 전략 실습 · 상품 ID와 유형을 함께 검증하기

실습 환경은 MySQL 8.4(InnoDB)다. 상품마다 유형을 하나 지정한다. 자식 테이블의 기본 키이자 외래 키의 일부인 `product_id`는 부모 한 건과 연결된다. 자식이 자신의 유형만 저장하도록 `CHECK`를 걸고, 외래 키에 유형을 포함해 부모의 유형과 일치하는지도 검사한다.

```sql
CREATE TABLE dd19_products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(80) NOT NULL,
    product_kind VARCHAR(8) NOT NULL,
    CHECK (product_kind IN ('DIGITAL', 'PHYSICAL')),
    UNIQUE (product_id, product_kind)
) ENGINE = InnoDB;

CREATE TABLE dd19_digital_products (
    product_id BIGINT PRIMARY KEY,
    product_kind VARCHAR(8) NOT NULL DEFAULT 'DIGITAL',
    file_size_mb DECIMAL(8, 2) NOT NULL,
    CHECK (product_kind = 'DIGITAL'),
    CHECK (file_size_mb > 0),
    FOREIGN KEY (product_id, product_kind)
        REFERENCES dd19_products (product_id, product_kind)
) ENGINE = InnoDB;

CREATE TABLE dd19_physical_products (
    product_id BIGINT PRIMARY KEY,
    product_kind VARCHAR(8) NOT NULL DEFAULT 'PHYSICAL',
    weight_g INT NOT NULL,
    CHECK (product_kind = 'PHYSICAL'),
    CHECK (weight_g > 0),
    FOREIGN KEY (product_id, product_kind)
        REFERENCES dd19_products (product_id, product_kind)
) ENGINE = InnoDB;

START TRANSACTION;
INSERT INTO dd19_products VALUES
    (101, 'Audio Course', 'DIGITAL'),
    (102, 'Sketchbook', 'PHYSICAL');
INSERT INTO dd19_digital_products (product_id, file_size_mb) VALUES (101, 32.50);
INSERT INTO dd19_physical_products (product_id, weight_g) VALUES (102, 240);
COMMIT;

SELECT p.product_id, p.product_kind, d.file_size_mb, f.weight_g
FROM dd19_products AS p
LEFT JOIN dd19_digital_products AS d ON d.product_id = p.product_id
LEFT JOIN dd19_physical_products AS f ON f.product_id = p.product_id
ORDER BY p.product_id;
```

조회에서 상품 101은 파일 크기 32.50과 무게 `NULL`, 상품 102는 파일 크기 `NULL`과 무게 240을 반환한다. 101에 실물 상세 행을 추가하면 부모의 유형이 다르므로 외래 키 검사에 실패한다. 여기서 부모에 있는 `UNIQUE(product_id, product_kind)`는 유형까지 비교할 외래 키가 참조하는 키다. [MySQL CHECK 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html) · [MySQL 외래 키 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)

이 DDL은 상품당 상세 행을 최대 한 건으로 제한한다. 부모를 넣은 뒤 상세 행을 누락하거나 상세만 삭제하면 상품 행은 남을 수 있다. 모든 상품에 상세가 반드시 있어야 한다면 등록과 변경을 한 트랜잭션의 쓰기 경로로 묶고, 완료 직전에 해당 유형의 상세가 정확히 하나 있는지 확인한다. ORM으로 매핑하더라도 물리 제약과 조회 SQL을 함께 점검한다. Jakarta Persistence 3.2는 단일 테이블과 조인 전략을 필수 지원으로 규정하고 구현 클래스별 전략을 선택 사항으로 둔다. [Jakarta Persistence 3.2 상속 매핑 지원 범위](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2#inheritance-mapping-strategies)
