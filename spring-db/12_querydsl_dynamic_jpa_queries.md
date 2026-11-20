# Querydsl Dynamic JPA Queries

## 1. 생성된 Q 타입으로 조건 작성하기

Querydsl JPA는 엔티티별 Q 타입을 생성해 속성과 연산을 Java 코드에서 표현한다. 문자열 JPQL에 적던 필드 이름을 Q 타입의 필드로 참조하므로 속성 이름이나 타입의 일부 변경을 컴파일 때 발견할 수 있다. JPA용 쿼리는 실행 시 JPQL로 변환되어 JPA 구현체를 거친다. [Querydsl 5.0 · JPAQueryFactory](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/JPAQueryFactory.java) · [Querydsl 5.0 · JPQL 쿼리](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/AbstractJPAQuery.java)

Spring Boot 3.x의 `jakarta.persistence` 엔티티를 처리하는 Querydsl 5 구성에서는 `querydsl-jpa`와 `querydsl-apt`의 `jakarta` 분류자를 사용한다. 컴파일 단계에서 애너테이션 프로세서가 [상품 엔티티](10_jpa_entity_mapping_and_repository_operations.md)의 `QCatalogItemEntity`를 생성한다. [Querydsl 5.0 · Jakarta 지원](https://github.com/querydsl/querydsl/releases/tag/QUERYDSL_5_0_0) · [Querydsl 5 빌드 구성](../querydsl/06_querydsl_5_configuration_for_spring_boot.md)

## 2. 값이 있는 조건만 조합하기

`BooleanBuilder`는 조건을 순차적으로 결합할 때 사용할 수 있다. 이름이나 최대 가격이 입력된 경우에만 해당 조건을 더한다.

```java
import java.util.List;

import com.querydsl.core.BooleanBuilder;
import com.querydsl.jpa.impl.JPAQueryFactory;

public class QuerydslCatalogSearch {

    private final JPAQueryFactory queries;

    public QuerydslCatalogSearch(JPAQueryFactory queries) {
        this.queries = queries;
    }

    public List<CatalogItemEntity> search(String keyword, Long maxPriceCents) {
        QCatalogItemEntity item = QCatalogItemEntity.catalogItemEntity;
        var conditions = new BooleanBuilder();

        if (keyword != null && !keyword.isBlank()) {
            conditions.and(item.name.contains(keyword));
        }
        if (maxPriceCents != null) {
            conditions.and(item.priceCents.loe(maxPriceCents));
        }

        return queries.selectFrom(item).where(conditions).orderBy(item.id.asc()).fetch();
    }
}
```

정렬과 페이징은 조회 쿼리에 명시한다. 전체 개수가 필요하면 조회 조건과 맞는 별도 건수 쿼리를 작성한다. Querydsl 5의 JPA용 `fetchCount()`와 `fetchResults()`는 사용 중단 대상으로 지정됐으며, 복잡한 그룹화 쿼리의 건수 계산에서 메모리 집계가 일어날 수 있다. [Querydsl 5.0 · BooleanBuilder 소스](https://raw.githubusercontent.com/querydsl/querydsl/QUERYDSL_5_0_0/querydsl-core/src/main/java/com/querydsl/core/BooleanBuilder.java) · [Querydsl 5.0 · 카운트 API](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/AbstractJPAQuery.java)
