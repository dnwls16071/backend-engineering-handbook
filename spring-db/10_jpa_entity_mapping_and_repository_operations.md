# JPA Entity Mapping and Repository Operations

## 1. 상품을 엔티티로 매핑하기

Jakarta Persistence(JPA)는 엔티티 매핑과 영속 상태를 다루는 표준이다. Hibernate는 그 표준을 구현한다. 애플리케이션은 엔티티와 작업 단위를 정의하고, 구현체가 매핑과 SQL 방언에 맞춰 JDBC를 통해 SQL을 실행한다. Spring Boot의 `spring-boot-starter-data-jpa`를 사용하면 일반적인 Hibernate 기반 구성을 시작할 수 있다. [Jakarta Persistence 3.1 · 명세](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Spring Boot 3.5 · JPA](https://docs.spring.io/spring-boot/3.5/reference/data/sql.html)

[상품 테이블](06_data_access_architecture_and_repository_design.md)의 ID는 DB가 생성한다. `@Id`를 필드에 두었으므로 JPA는 필드 접근으로 매핑한다.

```java
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "catalog_item")
public class CatalogItemEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "price_cents", nullable = false)
    private long priceCents;

    @Column(nullable = false)
    private int stock;

    protected CatalogItemEntity() {
    }

    public CatalogItemEntity(String name, long priceCents, int stock) {
        this.name = name;
        this.priceCents = priceCents;
        this.stock = stock;
    }

    public Long getId() {
        return id;
    }

    public void rename(String name) {
        this.name = name;
    }
}
```

## 2. EntityManager로 저장하고 조회하기

| 작업 | JPA 동작 |
| --- | --- |
| 생성 | 트랜잭션에서 `persist(entity)`를 호출해 엔티티를 영속 상태로 만든다. |
| 기본 키 조회 | `find(CatalogItemEntity.class, id)`는 관리 중인 엔티티나 조회 결과를 반환한다. 행이 없으면 `null`이다. |
| 수정 | 관리 중인 엔티티의 `rename(...)` 등을 호출한다. 변경은 플러시 시 SQL로 반영된다. |
| 검색 | JPQL에서 엔티티 이름과 속성을 사용한다. 예를 들어 `select i from CatalogItemEntity i where i.priceCents <= :maxPrice`다. |

플러시는 영속성 컨텍스트의 변경을 데이터베이스에 동기화한다. 트랜잭션 자체의 커밋은 매니저가 처리한다. ID 생성 방식이나 쿼리 실행 시점에 따라 SQL이 커밋 전에 실행될 수 있다. [Jakarta Persistence 3.1 · 영속성 컨텍스트와 플러시](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [JPA 영속성 컨텍스트](../jpa/02_jpa_persistence_context_and_entity_lifecycle.md)

## 3. Spring에서 작업 경계와 예외 처리하기

Spring 저장소에서는 `@PersistenceContext`로 현재 트랜잭션에 연결되는 `EntityManager`를 주입받을 수 있다. 서비스에서 `@Transactional`로 저장과 변경의 범위를 정한다. `@Repository` 빈에 Spring의 예외 변환 후처리기가 적용되면 저장소 호출에서 나온 지원 대상 영속성 예외를 `DataAccessException`으로 변환할 수 있다. 플러시나 커밋이 처음 실패하는 경우 예외는 서비스의 트랜잭션 종료 시점에 나타날 수 있다. [Spring Framework 6.2 · JPA와 예외 변환](https://docs.spring.io/spring-framework/reference/6.2/data-access/orm/jpa.html) · [Spring Framework 6.2 API · JpaTransactionManager](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/orm/jpa/JpaTransactionManager.html)
