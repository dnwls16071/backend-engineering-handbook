# JPA Relationship Mappings and Ownership

Jakarta Persistence 3.1에서 연관관계의 주인은 외래 키나 조인 테이블을 갱신할 쪽을 정한다. 객체에서 양쪽을 탐색할 수 있는지, 저장과 삭제를 전파할지, 언제 읽을지는 별도로 설정한다. 예제는 Hibernate ORM 6.6과 PostgreSQL 18을 기준으로 한다. [Jakarta Persistence 3.1 §2.10 및 §2.11](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

## 1. 다대일과 외래 키

여러 주문 항목이 주문 하나를 가리킨다. `OrderLine.order`의 기본 외래 키는 항목 테이블에 있고, 표준 기본 이름은 연관 속성명과 참조 기본 키 열을 합친 `order_id`다. `@ManyToOne`은 기본 `EAGER`, `optional = true`, 캐스케이드 없음이다. 항상 주문이 있어야 한다면 다음처럼 매핑하고 운영 DDL에도 `NOT NULL`과 외래 키를 정의한다. [Jakarta Persistence 3.1 §2.11.3.2 및 §11.1.30](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

```java
@Entity
class OrderLine {
    @Id @GeneratedValue
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "order_id", nullable = false)
    private PurchaseOrder order;
    private String sku;

    protected OrderLine() {}
    OrderLine(PurchaseOrder order, String sku) {
        this.order = order;
        this.sku = sku;
    }

    void detachFromOrder() { this.order = null; }
}
```

`LAZY`는 표준의 힌트다. `EAGER`도 SQL 조인을 강제하지 않으며 Hibernate가 보조 SELECT로 로딩할 수 있다. 목록에서 매번 주문 정보가 필요하면 `join fetch line.order`를 쓴 JPQL이나 엔티티 그래프로 필요한 데이터를 가져오고, 여러 항목을 조회했을 때 SQL 수를 확인한다. [Hibernate 6.6 페치 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)

## 2. 양방향 일대다와 `mappedBy`

`mappedBy = "order"`는 앞 예제의 `OrderLine.order` 자바 속성을 지목한다. 컬렉션은 역방향, `OrderLine.order`는 주인이다. 양쪽에 변경을 반영하는 메서드로 항목을 추가하거나 제거하면 메모리의 객체 그래프와 플러시 결과를 일치시킬 수 있다. `@OneToMany`의 기본 fetch 전략은 `LAZY`다. [Jakarta Persistence 3.1 §2.10 및 §11.1.40](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6 양방향 일대다](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-one-to-many-bidirectional)

```java
@Entity
class PurchaseOrder {
    @Id @GeneratedValue
    private Long id;

    @OneToMany(mappedBy = "order", cascade = CascadeType.PERSIST, orphanRemoval = true)
    private List<OrderLine> lines = new ArrayList<>();

    protected PurchaseOrder() {}
    OrderLine addLine(String sku) {
        OrderLine line = new OrderLine(this, sku);
        lines.add(line);
        return line;
    }

    void removeLine(OrderLine line) {
        if (lines.remove(line)) {
            line.detachFromOrder();
        }
    }
}
```

`PERSIST`는 주문의 영속화를 새 항목에도 전파한다. `orphanRemoval = true`는 관리 상태의 항목을 관계에서 제거했을 때 플러시에서 삭제하고 주문 자체를 삭제할 때도 항목을 삭제한다. 수명이 주문에 종속된 항목에 적용한다. 관계에서 제거한 항목을 다른 주문에 재할당하는 동작은 이식성이 보장되지 않는다. [Jakarta Persistence 3.1 §2.10](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

## 3. 단방향 일대다의 조인 테이블과 외래 키

주문에서만 항목을 탐색하고 `@OneToMany`만 선언하면 표준 기본 매핑은 조인 테이블이다. 조인 테이블에 주문과 항목을 가리키는 외래 키가 있으며 항목 쪽 키는 유일하다. Hibernate 6.6의 기본 조인 테이블을 쓰는 `List` 예제는 항목 하나를 빼면 주문의 연결 행을 모두 삭제하고 남은 연결을 다시 INSERT한다. [Jakarta Persistence 3.1 §2.11.5.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6 단방향 일대다](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-one-to-many-unidirectional)

```java
@OneToMany
@JoinColumn(name = "order_id")
private List<OrderLine> lines = new ArrayList<>();
```

위 대안에서는 항목 엔티티의 `order` 속성을 제거한다. 컬렉션이 항목 테이블의 `order_id`를 관리하고 조인 테이블은 생략된다. FK 갱신이 별도 UPDATE가 되는지는 설정과 작업에 따라 달라지므로 INSERT와 제거를 각각 플러시해 SQL을 확인한다. 항목이 많고 필터나 페이지 조회가 필요하면 항목에 `@ManyToOne`만 두고 `order_id`로 조회할 수 있다. PostgreSQL은 참조하는 FK 열에 인덱스를 자동 생성하지 않으므로 `order_line(order_id)` 인덱스를 조회 패턴에 맞춰 검토한다. [Jakarta Persistence 3.1 §11.1.25 및 §11.1.40](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6 연관관계 권장 사항](https://docs.hibernate.org/orm/6.6/userguide/html_single/#best-practices-associations) · [PostgreSQL 18 외래 키](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK)

## 4. 일대일의 유일성, `@MapsId`, 지연 로딩

독립 PK를 가진 주문 영수증에는 `order_id` FK와 `UNIQUE (order_id)`를 둔다. 영수증의 정체성이 주문에 종속된다면 다음처럼 `order_receipt.order_id`를 PK 겸 FK로 사용한다. `@MapsId`는 `order.id`에서 영수증의 식별자를 얻으므로 영수증을 영속화하기 전에 `order`를 설정한다. [Jakarta Persistence 3.1 §2.4.1 및 §2.11.3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)

```java
@Id
@Column(name = "order_id")
private Long id;

@MapsId
@OneToOne(fetch = FetchType.LAZY, optional = false)
@JoinColumn(name = "order_id", nullable = false)
private PurchaseOrder order;
```

`@OneToOne`은 기본 `EAGER`다. Hibernate 6.6에서 FK를 보유하지 않는 쪽의 `mappedBy` 속성은 연결된 행이 있는지 확인해야 한다. 바이트코드 향상을 적용하지 않으면 `LAZY`를 지정해도 보조 SELECT가 발생할 수 있다. 위 단방향 매핑에서는 필요할 때 `entityManager.find(OrderReceipt.class, orderId)`로 영수증을 조회할 수 있다. [Hibernate 6.6 양방향 일대일 지연 로딩](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-one-to-one-bidirectional-lazy)

## 5. 다대다를 연결 엔티티로 모델링하기

`@ManyToMany`는 연결 행에 별도 상태가 없는 관계를 조인 테이블로 표현한다. 양방향 매핑에서는 한쪽에 `@JoinTable`을 정의하고 반대쪽에 `mappedBy`를 둔다. 대상 엔티티는 여러 곳에서 공유될 수 있으므로 링크를 끊을 때 대상까지 삭제하는 `CascadeType.REMOVE`는 피한다. [Jakarta Persistence 3.1 §2.10 및 §2.11.4](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Hibernate 6.6 다대다](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-many-to-many)

수강 신청에 신청 시각과 상태가 생기면 `Enrollment`를 엔티티로 만든다. `student`와 `course`를 각각 `@ManyToOne(fetch = LAZY, optional = false)`로 매핑하고, 테이블은 두 FK와 `(student_id, course_id)` 유일성 제약을 가진다. 신청 자체를 참조할 일이 있으면 대리 PK를, 두 FK가 신청의 불변 식별자라면 `@EmbeddedId`와 두 `@MapsId`를 쓸 수 있다. 취소할 때는 취소 정책에 따라 `Enrollment` 상태를 바꾸거나 행을 삭제한다. 학생과 강의는 독립적으로 관리한다. [Hibernate 6.6 연결 엔티티 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-many-to-many-bidirectional-with-link-entity-lifecycle-example) · [Jakarta Persistence 3.1 §2.4.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)
