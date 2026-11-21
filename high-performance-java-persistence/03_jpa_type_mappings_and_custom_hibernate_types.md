# JPA Type Mappings and Custom Hibernate Types

Hibernate의 기본 값 매핑에는 Java 값의 표현, JDBC 바인딩 방식, 데이터베이스 컬럼 타입이 관여한다. 세 요소를 확인하면 SQL에 어떤 값이 전달되는지 추적할 수 있다. [Hibernate 기본 값과 합성 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#basic) · [Jakarta Persistence 3.1 명세](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 1. JPA 기본 타입과 Hibernate의 타입 해석

JPA는 기본 속성, 임베디드 값, 연관관계처럼 모델을 표현하는 매핑을 정의한다. Hibernate 6.6은 기본 속성에 `JavaType`과 `JdbcType`을 조합한다. `JavaType`은 값의 비교, 복제 및 변환에 관여하고, `JdbcType`은 PreparedStatement 바인딩과 ResultSet 추출을 처리한다. 방언은 DB가 사용하는 DDL 타입 결정에 관여한다. [Hibernate 합성 타입](https://docs.hibernate.org/orm/6.6/introduction/html_single/#compositional-basic)

| 속성 | 매핑에서 확인할 점 |
| --- | --- |
| `BigDecimal` | 정밀도와 소수점 자릿수, DB의 반올림 동작 |
| `Enum` | `EnumType.STRING`이면 상수 이름 변경 시 기존 데이터도 마이그레이션 필요 |
| `LocalDate` | 시간대 없는 달력 날짜라는 의미와 `DATE` 매핑 |
| JSON 값 | 물리 타입과 JSON 직렬화, 쿼리 연산자 및 인덱스 지원 |

## 2. 사용자 정의 타입 선택하기

`AttributeConverter<X,Y>`는 Java 도메인 값 `X`를 JDBC가 매핑할 수 있는 Java 값 `Y`로 변환할 때 사용한다. 표준 JPA 확장 지점이므로 예를 들어 SKU 값 객체를 `String`으로 저장하는 데 적합하다. 자동 변환의 이식성이 필요한 경우 기본 값 속성에 적용한다. 식별자·버전·연관관계나 `@Enumerated`, `@Temporal` 속성에 대한 변환은 이식 가능한 계약에 포함되지 않는다. [Jakarta Persistence 3.1 §3.8과 §11.1.10](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

```java
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

record Sku(String value) {}

@Converter(autoApply = true)
public class SkuConverter implements AttributeConverter<Sku, String> {
    @Override
    public String convertToDatabaseColumn(Sku sku) {
        return sku == null ? null : sku.value();
    }

    @Override
    public Sku convertToEntityAttribute(String value) {
        return value == null ? null : new Sku(value);
    }
}
```

Hibernate에서 PostgreSQL JSON 컬럼을 다룰 때는 `@JdbcTypeCode(SqlTypes.JSON)`으로 타입을 명시할 수 있다. JSON 포맷 매퍼와 실제 컬럼 타입을 함께 검증한다. 커스텀 비교나 저수준 JDBC 변환이 필요하면 Hibernate의 `JavaType`·`JdbcType` 조합이나 `UserType<T>`을 고려한다. 가변 객체가 포함되면 복사 방식과 변경 감지, 2차 캐시에서 값을 분해하고 복원하는 동작까지 테스트한다. [Hibernate JSON과 사용자 정의 타입](https://docs.hibernate.org/orm/6.6/userguide/html_single/#basic-mapping-custom)
