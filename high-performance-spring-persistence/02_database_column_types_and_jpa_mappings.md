# Database Column Types and JPA Mappings

컬럼 타입을 정할 때 값의 범위, 정밀도, `NULL`의 의미와 검색 방식을 확인한다. SQL 예시는 PostgreSQL 17을 사용하며, Java 예시는 Spring Boot 3.5, Spring Data JPA 3.5, Hibernate ORM 6.6과 Jakarta Persistence 3.1을 기준으로 한다. [PostgreSQL 데이터 타입](https://www.postgresql.org/docs/17/datatype.html) · [Spring Boot 3.5 의존성 버전](https://docs.spring.io/spring-boot/3.5/appendix/dependency-versions/coordinates.html)

## 1. 기본 컬럼 타입과 크기 선택

| 분류 | PostgreSQL 타입 | Java 매핑 예 |
| --- | --- | --- |
| 정수 | `smallint`, `integer`, `bigint` | `Short`, `Integer`, `Long` |
| 정확한 소수 | `numeric(p, s)` | `BigDecimal` |
| 근사 실수 | `real`, `double precision` | `Float`, `Double` |
| 문자열 | `varchar(n)`, `text` | `String` |
| 날짜와 시간 | `date`, `timestamp`, `timestamptz` | `LocalDate`, `LocalDateTime`, `OffsetDateTime` |
| 논리 및 바이너리 | `boolean`, `bytea` | `Boolean`, `byte[]` |

`smallint`, `integer`, `bigint`의 데이터 영역은 각각 2, 4, 8바이트다. 상태 코드처럼 범위가 작은 값에는 `smallint`를 고려하고, ID나 누적 카운터는 증가량을 예상해 타입을 정한다. 컬럼과 인덱스 키가 작아지면 페이지당 저장할 수 있는 값이 늘어날 수 있다. 전체 크기는 행과 인덱스의 오버헤드, 정렬을 위한 패딩, 가변 길이 값의 저장 방식에도 좌우된다. PostgreSQL의 `varchar(n)`은 문자 수를 제한하고, `char(n)`은 공백을 채운다. `text`와 `varchar`의 길이 선택은 데이터 규칙에 맞춘다. [PostgreSQL 숫자 타입](https://www.postgresql.org/docs/17/datatype-numeric.html) · [문자 타입](https://www.postgresql.org/docs/17/datatype-character.html) · [페이지 레이아웃](https://www.postgresql.org/docs/17/storage-page-layout.html)

`numeric(12, 2)`의 정밀도 12는 전체 자릿수이고 스케일 2는 소수점 이하 자릿수다. 최대 정수부는 10자리다. PostgreSQL은 입력을 먼저 지정된 소수 자릿수로 반올림하고, 그 결과의 정수부가 범위를 넘으면 오류를 낸다. 업무에서 소수점 셋째 자리 입력 자체를 거부해야 한다면 DB에 보내기 전에 검증한다. 컬럼 제약을 Flyway SQL로 적용하고 엔티티의 `@Column` 메타데이터도 맞춘다. [PostgreSQL `numeric` 규칙](https://www.postgresql.org/docs/17/datatype-numeric.html#DATATYPE-NUMERIC-DECIMAL) · [Jakarta Persistence `@Column`](https://jakarta.ee/specifications/persistence/3.1/apidocs/jakarta.persistence/jakarta/persistence/column)

```sql
amount numeric(12, 2) NOT NULL CHECK (amount >= 0)
```

```java
@Column(nullable = false, precision = 12, scale = 2)
private BigDecimal amount;
```

시간 값은 의미에 맞춰 매핑한다. 현지 시각 자체를 저장하는 `timestamp`는 `LocalDateTime`에 대응한다. 사건 발생 시점을 나타내는 PostgreSQL의 `timestamptz`는 UTC로 정규화해 저장하고 세션 시간대에 맞춰 출력한다. 입력 당시의 시간대나 오프셋을 보존해야 하면 별도 컬럼에 저장한다. 다른 엔진에 옮길 때에는 정수 범위, 문자열 길이 단위와 시간대 동작을 해당 엔진에서 확인한다. [PostgreSQL 날짜·시간 타입](https://www.postgresql.org/docs/17/datatype-datetime.html) · [Hibernate 시간대 저장](https://docs.hibernate.org/orm/6.6/userguide/html_single/#basic-datetime-timezone)

## 2. Stack Overflow 공개 스키마에서 타입 선택 읽기

Stack Exchange가 공개한 Data Explorer 및 데이터 덤프 스키마에서 `Posts`는 질문과 답변을 한 테이블에 담는다. `PostTypeId`가 질문(`1`)과 답변(`2`)을 구분하고, 답변의 `ParentId`가 원래 질문을 가리킨다. `Title`은 질문 등에 사용하며, `CreationDate`와 `Score`는 게시물의 생성 시점과 점수를 기록한다. 공개 Data Explorer에서 정확한 컬럼 타입과 길이는 문서에 연결된 T-SQL 메타데이터 쿼리로 확인할 수 있다. [Stack Exchange 공개 스키마](https://meta.stackexchange.com/questions/2677/database-schema-documentation-for-the-public-data-dump-and-sede)

아래는 공개 스키마에서 질문과 답변의 구조만 가져와 만든 PostgreSQL 실습용 테이블이다. 두 종류의 게시물만 받는 `CHECK`와 자기 참조 외래 키는 실습에서 정한 제약이다. ID는 `bigint`, 종류 코드는 `smallint`, 음수도 가능한 점수는 `integer`로 정하고, 발생 시점은 `timestamptz`로 저장한다.

```sql
CREATE TABLE posts (
    id bigint PRIMARY KEY,
    post_type_id smallint NOT NULL CHECK (post_type_id IN (1, 2)),
    parent_id bigint REFERENCES posts (id),
    creation_date timestamptz NOT NULL,
    score integer NOT NULL,
    title text,
    body text NOT NULL
);
```

이 구조에서 답변을 가져오는 조건은 `WHERE parent_id = ?`다. 해당 조회의 빈도가 높다면 `parent_id` 인덱스를 검토한다. PostgreSQL은 외래 키를 선언할 때 참조하는 쪽 컬럼에 인덱스를 자동 생성하지 않는다. [PostgreSQL 외래 키](https://www.postgresql.org/docs/17/ddl-constraints.html#DDL-CONSTRAINTS-FK)

## 3. PostgreSQL 전용 타입과 JPA 매핑

PostgreSQL은 `inet`, 범위 타입과 `jsonb`처럼 자체 연산을 제공하는 타입을 지원한다. 예를 들어 `jsonb`는 JSON을 분해된 바이너리 형식으로 저장한다. 객체 키의 순서와 공백을 보존하지 않으며, 포함 연산자(`@>`)와 GIN 인덱스를 사용할 수 있다. 문서 내부 값으로 조회하는 경우 사용하는 연산자와 조건에 맞춰 인덱스를 설계한다. [PostgreSQL 타입 목록](https://www.postgresql.org/docs/17/datatype.html) · [PostgreSQL JSON 타입과 인덱스](https://www.postgresql.org/docs/17/datatype-json.html)

JSON 문서를 문자열로 저장하는 설계라면 JPA의 `AttributeConverter<Metadata, String>`으로 값 객체와 `text` 컬럼 사이를 변환할 수 있다. `AttributeConverter`의 두 번째 타입은 JDBC가 컬럼과 주고받을 Java 타입이다. 문자열 변환만 추가한 상태에서 컬럼을 `jsonb`로 바꾸면 PostgreSQL이 요구하는 JDBC 바인딩까지 함께 바뀌지 않는다. `columnDefinition`은 스키마 생성 시 사용하는 DDL 조각을 지정한다. [Jakarta Persistence `AttributeConverter`](https://jakarta.ee/specifications/persistence/3.1/apidocs/jakarta.persistence/jakarta/persistence/attributeconverter) · [Jakarta Persistence `@Column`](https://jakarta.ee/specifications/persistence/3.1/apidocs/jakarta.persistence/jakarta/persistence/column)

`jsonb`를 쓰는 경우 Flyway에서 `metadata jsonb` 컬럼을 만들고 Hibernate의 `@JdbcTypeCode(SqlTypes.JSON)`으로 JSON 타입 매핑을 요청한다. Hibernate는 클래스패스의 JSON 직렬화 라이브러리(예를 들어 Jackson)를 사용한다. 아래 예시는 문자열 값을 갖는 JSON 객체를 매핑한다. [Hibernate 6.6 JSON 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#basic-mapping-json)

```java
import java.util.Map;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@JdbcTypeCode(SqlTypes.JSON)
private Map<String, String> metadata;
```

`@JdbcTypeCode`는 Hibernate에 의존하고, `jsonb`와 해당 연산자 및 인덱스는 PostgreSQL에 의존한다. 공급자나 엔진을 바꿀 가능성이 높고 JSON 전체만 읽고 쓴다면, 표준 JPA 변환기와 대상 엔진이 지원하는 문자열 컬럼의 조합이 적용 범위를 넓힌다. `jsonb`를 선택했다면 실제 PostgreSQL 테스트에서 저장 후 재조회, `NULL`과 빈 객체의 구분, 검색 연산의 결과를 확인한다. [Hibernate 6.6 JSON 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#basic-mapping-json) · [PostgreSQL JSON 연산자](https://www.postgresql.org/docs/17/functions-json.html)
