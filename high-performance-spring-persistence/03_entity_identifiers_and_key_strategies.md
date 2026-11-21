# Entity Identifiers and Key Strategies

Spring Boot 3.5, Spring Data JPA 3.5, Hibernate ORM 6.6, Jakarta Persistence 3.1을 기준으로 키의 의미, 값의 할당 시점, INSERT 배치에 미치는 영향을 살펴본다. SQL 예제는 PostgreSQL 18을 사용한다.

## 1. 자연 키와 대리 키

자연 키는 도메인에서 이미 유일한 값이다. 예를 들어 통화 목록에서 코드가 영구적으로 유일하고 불변이라는 계약이 있으면 `currency_code`를 기본 키로 쓸 수 있다. 기본 키의 폭이나 구성 열이 늘면 이를 참조하는 외래 키와 인덱스에도 같은 키가 들어간다. Jakarta Persistence에서 영속화한 엔티티의 기본 키를 변경하면 동작이 정의되지 않는다. [Jakarta Persistence 3.1 §2.4](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

공급사 상품 코드가 정정될 수 있다면 `id`를 대리 키로 두고 주문 항목에서 `id`를 참조한다. 업무상 중복 금지는 `(supplier_id, supplier_sku)`의 `UNIQUE`와 `NOT NULL`로 보장한다. Hibernate의 `@NaturalId(mutable = true)`는 수정 가능한 업무 키에 대한 전용 조회를 제공한다. 아래 DDL은 공급사 테이블 `supplier(id)`가 있다고 가정한다. [Hibernate 6.6 자연 키](https://docs.hibernate.org/orm/6.6/userguide/html_single/#naturalid) · [PostgreSQL 18 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html)

```sql
CREATE TABLE supplier_product (
    id bigint PRIMARY KEY,
    supplier_id bigint NOT NULL REFERENCES supplier (id),
    supplier_sku text NOT NULL,
    UNIQUE (supplier_id, supplier_sku)
);
```

## 2. 할당 식별자와 Spring Data의 신규 엔티티 판별

할당 식별자는 애플리케이션이 영속화 전에 값을 넣은 `@Id`다. Spring Data JPA의 `save()`는 신규로 판정하면 `persist()`, 그 외에는 `merge()`를 호출한다. 기본 판정은 먼저 `Long` 같은 참조형 `@Version`의 `null`을 검사하고, 참조형 버전 속성이 없으면 식별자를 검사한다. `Long` 식별자가 `null`이면 신규다. 원시형 버전의 `0`은 첫 저장 버전이 될 수 있으므로 버전 기반 판정에 쓰이지 않는다. [Spring Data JPA 3.5 엔티티 저장](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html)

버전이 없는 신규 엔티티에 외부 시스템의 주문 번호가 이미 채워져 있으면 기본 판정은 `merge()`를 선택한다. Hibernate가 기존 행을 찾기 위해 SELECT를 실행할 수 있고, `merge()` 경로에서는 반환된 관리 인스턴스를 사용해야 한다. 낙관적 잠금이 필요한 엔티티는 참조형 `@Version`을 매핑할 수 있다. 버전 필드 없이 저장 경로를 제어하려면 `Persistable.isNew()`를 구현한다. [Spring Data JPA 3.5 엔티티 저장](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html) · [Jakarta Persistence 3.1 §3.2.7.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

```java
@Entity
class ImportedOrder implements Persistable<String> {
    @Id
    private String id;

    @Transient
    private boolean newEntity = true;

    protected ImportedOrder() {}

    ImportedOrder(String externalOrderNumber) {
        this.id = Objects.requireNonNull(externalOrderNumber);
    }

    @Override
    public String getId() { return id; }

    @Override
    public boolean isNew() { return newEntity; }

    @PostPersist
    @PostLoad
    void markExisting() { newEntity = false; }
}
```

이 플래그는 객체의 생명주기를 나타낸다. `@PostPersist`는 INSERT 이후 커밋 전에 실행될 수 있으므로 롤백한 인스턴스는 버리고 새 트랜잭션에서 다시 생성하거나 조회한다. 수정 요청은 관리 엔티티를 읽어 필요한 속성을 바꾼다. 이미 있는 번호로 새 객체를 만들고 `save()`하면 `persist()`를 선택하며, PK 제약에 따라 실패할 수 있다. [Spring Data JPA 3.5의 `Persistable` 예제](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html) · [Jakarta Persistence 3.1 §3.3.3 및 §3.5.3](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

## 3. 생성 식별자와 JDBC 배치

| 전략 | 값 생성과 Hibernate 6.6에서의 영향 |
| --- | --- |
| `SEQUENCE` | INSERT 전에 DB 시퀀스에서 값을 확보한다. 여러 식별자를 미리 할당하고 엔티티 INSERT를 JDBC 배치로 보낼 수 있다. |
| `IDENTITY` | DB가 INSERT에서 값을 생성한다. Hibernate 6.6은 이 전략을 쓰는 엔티티의 INSERT를 JDBC 배치로 묶지 않는다. |
| `TABLE` | 생성기 테이블에서 값을 할당한다. 같은 생성기 행을 여러 트랜잭션이 갱신하면 잠금 경합이 생길 수 있다. 엔티티 INSERT 전 키를 확보할 수 있다. |
| `AUTO` | `java.util.UUID` 타입에는 표준상 `UUID`와 같다. 그 외에는 JPA 구현체가 전략을 선택한다. Hibernate 6.6에서 `Long` 같은 수치형의 기본 구현인 `SequenceStyleGenerator`는 DB가 시퀀스를 지원하면 시퀀스를, 그 외에는 테이블을 사용한다. |
| `UUID` | Jakarta Persistence 3.1이 추가한 표준 전략이다. Hibernate 6.6은 기본적으로 랜덤 버전 4 UUID를 애플리케이션에서 생성한다. 키를 미리 알 수 있어 엔티티 INSERT 배치가 가능하다. |

`SEQUENCE`, `TABLE`, `UUID`로 키를 미리 확보하더라도 Hibernate의 `hibernate.jdbc.batch_size`가 양수여야 JDBC 배치가 활성화된다. Spring Boot에서 `spring.jpa.properties.hibernate.jdbc.batch_size=50`으로 전달할 수 있다. 같은 SQL을 사용하는 INSERT가 플러시에서 묶이는지 JDBC 배치 실행 횟수로 확인한다. [Jakarta Persistence 3.1 §11.1.20](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6 식별자 생성](https://docs.hibernate.org/orm/6.6/userguide/html_single/#identifiers-generators) · [Hibernate 6.6 JDBC 배치](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch-session-batch) · [Spring Boot 3.5 JPA 설정](https://docs.spring.io/spring-boot/3.5/how-to/data-access.html#howto.data-access.configure-jpa-properties)

## 4. 시퀀스의 설정, 이식성, 마이그레이션

PostgreSQL에서 새 `purchase_order` 테이블을 도입하는 예다. 매핑의 `sequenceName`을 DDL과 맞춘다. Hibernate의 `pooled`나 `pooled-lo` 최적화에서 `allocationSize = 50`을 쓰면 DB의 `INCREMENT BY`도 `50`으로 맞춘다. `allocationSize`는 Hibernate가 확보하는 식별자 범위의 크기이고, PostgreSQL의 `CACHE`는 DB 세션의 시퀀스 값 선할당 수다. 롤백이나 프로세스 재시작으로 번호에 빈 구간이 생길 수 있다. [Hibernate 6.6 시퀀스 설정](https://docs.hibernate.org/orm/6.6/introduction/html_single/Hibernate_Introduction.html) · [PostgreSQL 18 `CREATE SEQUENCE`](https://www.postgresql.org/docs/18/sql-createsequence.html) · [PostgreSQL 18 시퀀스 함수](https://www.postgresql.org/docs/18/functions-sequence.html)

```java
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "purchase_order_ids")
@SequenceGenerator(name = "purchase_order_ids", sequenceName = "purchase_order_seq",
                   initialValue = 1, allocationSize = 50)
private Long id;
```

```sql
CREATE SEQUENCE purchase_order_seq AS bigint START WITH 1 INCREMENT BY 50;
```

기존 데이터를 가져올 때는 쓰기를 멈추고 다른 인스턴스가 확보한 ID 범위를 폐기한 뒤 재시작 값을 적용한다. Hibernate 6 마이그레이션 가이드의 `pooled` 방식에서 가져온 최대 ID가 `100000`이면 `ALTER SEQUENCE purchase_order_seq RESTART WITH 100051`로 시작할 수 있다. 이미 운영 중인 시퀀스라면 다른 소비자와 기존 할당 범위를 함께 확인해 값을 뒤로 돌리지 않는다. Hibernate 5에서 올릴 때는 암묵적 `hibernate_sequence`가 엔티티별 시퀀스로 바뀔 수 있고 암묵적 할당 크기도 `50`이므로, 마이그레이션과 초기 데이터 SQL을 함께 검토한다. [Hibernate 6 마이그레이션 가이드](https://docs.hibernate.org/orm/6.0/migration-guide/#implicit-identifier-sequence-and-table-name) · [PostgreSQL 18 `ALTER SEQUENCE`](https://www.postgresql.org/docs/18/sql-altersequence.html)

`@SequenceGenerator`는 표준 매핑이며 실제 시퀀스 DDL과 지원 여부는 DB에 달려 있다. 시퀀스가 없는 DB나 다른 JPA 구현체로 옮길 때는 새 환경에서 생성기에 필요한 테이블 또는 열, 키 할당 시점, INSERT 배치가 유지되는지 확인한다. `AUTO`로 맡겼다면 이 부분도 대상 구현체와 방언에서 확인한다. [Jakarta Persistence 3.1 §11.1.20](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6의 `AUTO` 해석](https://docs.hibernate.org/orm/6.6/userguide/html_single/#identifiers-generators-auto)
