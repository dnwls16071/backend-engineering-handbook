# JPA Association Mappings and Entity Equality

연관관계 매핑은 FK의 위치와 갱신 주체, 객체 탐색 방향, 조회 시점을 결정한다. 객체에서 양방향으로 접근하더라도 FK를 기록하는 쪽은 하나다. [Jakarta Persistence 3.1 §2.10과 §2.11](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 1. JPA와 Hibernate의 연관관계 매핑

연관관계의 주인이 FK나 조인 테이블의 변경을 결정한다. 반대편의 `mappedBy`에는 주인을 가리키는 Java 속성 이름을 적는다. `cascade`는 어떤 엔티티 연산을 상대에게 전파할지 정하고, 페치 설정은 읽기 시점에 관여한다. JPA 기본 페치는 to-one에서 EAGER, to-many에서 LAZY다. JPA의 LAZY는 힌트이며 EAGER는 필요한 데이터를 미리 로드하라는 요구다. SQL 조인 사용 여부는 실행 경로와 구현에 달려 있다. [Hibernate 연관관계](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations) · [Hibernate 페칭](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)

## 2. 엔티티의 equals와 hashCode

같은 영속성 컨텍스트는 같은 식별자의 관리 인스턴스를 재사용한다. 서로 다른 컨텍스트에서 읽거나 분리한 객체는 Java 참조가 달라질 수 있다. 생명주기를 넘어서 비교해야 한다면, 생성 시점에 채우고 변경하지 않는 유일한 업무 키가 있는지 먼저 검토한다. DB의 업무 키 제약과 Java의 동등성 기준을 일치시킨다. [Hibernate equals와 hashCode](https://docs.hibernate.org/orm/6.6/userguide/html_single/#mapping-model-pojo-equalshashcode)

생성 식별자를 사용한다면 서로 다른 transient 객체가 `id == null`일 때 같다고 판정하면 안 된다. `HashSet`에 넣은 뒤 ID가 배정되어 해시 코드가 바뀌면 들어 있는 객체를 찾지 못할 수 있다. ID 비교를 택한 구현은 엔티티 타입과 프록시의 비교 방식을 정의하고, 식별자가 배정되는 전후에 해시 값이 안정적인지 테스트한다. 연관관계나 수정 가능한 필드를 비교 기준에 넣으면 지연 로딩과 순환 참조에도 영향을 받는다. [Hibernate 6 엔티티 동등성](https://docs.hibernate.org/orm/6.6/introduction/html_single/)

## 3. Many-to-One과 One-to-Many

주문과 주문 항목에서 `OrderLine.order`가 `order_line.order_id`를 소유하고, `Order.lines`의 `mappedBy = "order"`가 그 속성을 가리키도록 설계할 수 있다. 추가 메서드는 컬렉션에 삽입하고 자식의 `order`도 지정한다. 자식이 주문에 완전히 종속된다면 `orphanRemoval=true`로 관계에서 제거할 때 삭제를 요청할 수 있다. 자식을 공유하거나 따로 관리한다면 삭제 전파의 의미부터 확인한다. [Hibernate 양방향 OneToMany](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-one-to-many-bidirectional)

```java
// Order의 필드와 연관관계 변경 메서드
@OneToMany(mappedBy = "order", cascade = CascadeType.PERSIST, orphanRemoval = true)
private List<OrderLine> lines = new ArrayList<>();

public void addLine(OrderLine line) {
    lines.add(line);
    line.order = this;
}
```

이 예의 `OrderLine.order`에는 `@ManyToOne(fetch = FetchType.LAZY)`와 `@JoinColumn(name = "order_id", nullable = false)`를 매핑한다.

## 4. One-to-One과 공유 기본 키

일대일을 보장하려면 FK에 UNIQUE 제약을 두거나 종속 테이블의 PK를 FK로 겸용한다. 후자는 상세 엔티티에서 `@MapsId`로 부모의 식별자를 공유할 수 있다. 역방향의 선택적 일대일은 부모 행만 보고 상세 행 존재 여부를 알 수 없어 추가 쿼리가 발생할 수 있다. 지연 로딩 동작은 방향과 Hibernate enhancement 적용 여부를 포함해 확인한다. [Hibernate OneToOne](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-one-to-one)

## 5. Many-to-Many와 조인 엔티티

`@ManyToMany`는 두 엔티티의 관계를 조인 테이블에 기록한다. 가입 시각이나 역할처럼 관계 자체에 값이 생기면 조인 행을 별도의 엔티티로 매핑하고 양쪽을 `@ManyToOne`으로 연결한다. 공유 대상의 삭제까지 전파하면 다른 행에 영향을 줄 수 있으므로 연결 해제와 대상 삭제를 별도 연산으로 설계한다. [Hibernate ManyToMany](https://docs.hibernate.org/orm/6.6/userguide/html_single/#associations-many-to-many)
