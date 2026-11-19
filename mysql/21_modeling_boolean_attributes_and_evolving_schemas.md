# Modeling Boolean Attributes and Evolving Schemas

예·아니오 속성이 많은 서비스에서는 값의 뜻과 바뀌는 빈도를 먼저 정한다. 예를 들어 계정의 알림 설정에는 동의(`1`), 거부(`0`), 아직 응답하지 않은 상태가 있다. 응답하지 않은 상태를 거부와 구분해야 한다면 값의 부재에 다른 의미를 부여한다. 실습 환경은 MySQL 8.4(InnoDB)다.

## 1. 논리 모델에서 뜻을 고정

속성마다 이름, 적용 대상, 기본값, 필수 여부를 정한다. 같은 속성을 사용자별로 한 번 설정할 수 있다면 `(account_id, flag_code)`가 유일하다. 거부와 미응답의 차이가 중요하면 `0`을 명시적으로 저장하고 행이 없는 경우를 미응답으로 해석할 수 있다. 이력이 필요하다면 누가 언제 값을 바꿨는지도 모델에 포함한다.

## 2. 물리 모델 선택

| 방식 | 적합한 경우와 비용 |
| --- | --- |
| 앵커 엔터티별 단일 테이블 | 계정처럼 기준이 되는 엔터티 한 테이블에 안정적인 플래그를 컬럼으로 둔다. 필수 값과 자료형을 표현하기 쉽지만 플래그마다 스키마 변경이 필요하다. |
| 사이드 테이블 | 드물게 채워지거나 자주 함께 사용하는 플래그 묶음을 기본 키를 공유하는 별도 테이블에 둔다. 읽을 때 조인이 필요하다. |
| EAV | 속성 정의가 자주 바뀌거나 값이 드문 경우, 엔터티·속성 코드·값을 행으로 둔다. 속성별 자료형과 제약, 여러 속성을 한 번에 검색하는 방법을 설계해야 한다. |
| JSON 속성 | 변동이 잦고 주로 엔터티와 함께 읽는 속성 묶음을 한 컬럼에 둔다. 자주 필터링하는 경로는 생성 열 또는 함수 인덱스로 노출할 수 있다. |

[Entity-Attribute-Value Modeling](../database-design/20_entity_attribute_value_modeling.md) · [EAV Modeling Guidelines](https://pmc.ncbi.nlm.nih.gov/articles/PMC2110957/) · [MySQL JSON Data Type](https://dev.mysql.com/doc/refman/8.4/en/json.html)

## 3. 실습 · 명시적 거부와 값의 부재

다음은 알림 설정처럼 불리언 속성만 허용하는 EAV 예제다. 플래그 정의와 계정의 외래 키도 함께 유지한다.

```sql
CREATE TABLE mysql_lab_flag_accounts (
    account_id INT PRIMARY KEY
) ENGINE = InnoDB;

CREATE TABLE mysql_lab_flag_definitions (
    flag_code VARCHAR(24) PRIMARY KEY
) ENGINE = InnoDB;

CREATE TABLE mysql_lab_flag_values (
    account_id INT NOT NULL,
    flag_code VARCHAR(24) NOT NULL,
    flag_value TINYINT NOT NULL CHECK (flag_value IN (0, 1)),
    PRIMARY KEY (account_id, flag_code),
    FOREIGN KEY (account_id) REFERENCES mysql_lab_flag_accounts (account_id),
    FOREIGN KEY (flag_code) REFERENCES mysql_lab_flag_definitions (flag_code)
) ENGINE = InnoDB;

INSERT INTO mysql_lab_flag_accounts VALUES (1), (2), (3);
INSERT INTO mysql_lab_flag_definitions VALUES ('SMS_NOTICES');
INSERT INTO mysql_lab_flag_values VALUES (1, 'SMS_NOTICES', 1), (2, 'SMS_NOTICES', 0);

SELECT a.account_id, f.flag_value
FROM mysql_lab_flag_accounts AS a
LEFT JOIN mysql_lab_flag_values AS f
    ON f.account_id = a.account_id AND f.flag_code = 'SMS_NOTICES'
ORDER BY a.account_id;
```

조회 결과는 각각 `1`, `0`, `NULL`이다. 여러 플래그 조합으로 계정을 자주 찾으면 조회별 인덱스와 조인 비용을 측정한다. 핵심 조건에 자주 쓰는 안정적인 속성은 컬럼으로 옮기고 나머지를 EAV나 JSON에 둘 수 있다.

## 4. 스키마 변경을 서비스 배포와 맞추기

새 컬럼이나 테이블을 추가한 뒤 기존 버전의 애플리케이션과 함께 동작하도록 배포한다. 과거 데이터를 작은 배치로 채우고 누락과 값 차이를 검사한 다음 읽기를 전환한다. 이전 형식은 전환이 확인된 뒤 제거한다. MySQL에서는 변경 종류에 따라 온라인 DDL의 알고리즘과 잠금 조건이 달라지므로 대표 데이터에서 동작을 확인한다. [InnoDB Online DDL Operations](https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html) · [Generated Column Index Optimization](https://dev.mysql.com/doc/refman/8.4/en/generated-column-index-optimizations.html)
