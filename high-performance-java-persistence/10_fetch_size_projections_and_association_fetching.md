# Fetch Size, Projections, and Association Fetching

조회 비용은 서버가 처리한 행, JDBC가 가져온 행, Hibernate가 만든 객체의 수에 좌우된다. 호출이 필요한 데이터 범위를 정하고 DB 실행에서 객체 접근까지 비용을 확인한다. [Hibernate 페치 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)

## 1. Statement Fetch Size

`Statement.setFetchSize(n)`은 JDBC 드라이버가 한 번에 가져올 행 수에 관한 힌트다. PostgreSQL JDBC에서 커서 기반 조회를 사용하려면 자동 커밋이 꺼져 있고 ResultSet이 전방 전용이며 양수 fetch size가 설정되어 있어야 한다. 커서를 소비하는 동안 연결과 트랜잭션이 열린다. 작은 fetch size는 네트워크 왕복을 늘릴 수 있고, 큰 값은 버퍼 사용량을 늘릴 수 있다. [pgJDBC 커서 기반 조회](https://jdbc.postgresql.org/documentation/query/#getting-results-based-on-a-cursor)

## 2. Result Set 크기 줄이기

행 수를 줄이려면 `WHERE`와 정렬 조건을 설계하고 `setMaxResults()`나 SQL의 행 제한을 사용한다. 열 수는 필요한 데이터만 투영해 줄인다. 예를 들어 주문 목록에서 `id`와 `createdAt`만 읽으면 큰 설명 컬럼을 전송할 필요가 줄어든다. 페이징 정렬에는 `id` 같이 동률을 해소하는 열을 포함한다. fetch size를 낮춰도 대상 행을 끝까지 소비하면 총 행 수는 그대로다. [Jakarta Persistence 3.1 Query API](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 3. JPA 쿼리 프로젝션

단일 값은 해당 Java 타입으로 받을 수 있다. 여러 값을 타입으로 묶을 때 표준 JPQL의 `select new`에 DTO의 전체 클래스 이름을 적고 인자의 순서 및 타입을 생성자와 맞춘다. 단순 값으로 구성한 DTO는 영속성 컨텍스트의 관리 엔티티가 아니다.

```jpql
select new example.OrderSummary(o.id, o.createdAt)
from PurchaseOrder o
where o.customer.id = :customerId
order by o.createdAt desc, o.id desc
```

예제의 DTO는 `example.OrderSummary(Long id, Instant createdAt)` 생성자를 갖는다고 가정한다. [Jakarta Persistence 3.1 §4.8](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 4. Hibernate 쿼리 프로젝션

Hibernate 6 HQL은 여러 select 항목을 지정하고 `Session.createQuery(hql, OrderSummary.class)`에 결과 타입을 전달해 생성자로 패키징할 수 있다. 이때 조회 항목의 순서와 타입은 생성자와 일치해야 한다. 행을 사용자 정의 방식으로 변환할 때는 Hibernate의 `TupleTransformer`를 사용할 수 있다. 동일 쿼리를 다른 JPA 구현체로 옮길 수 있어야 하면 JPQL 생성자 표현식이 이식 가능한 선택이다. [Hibernate HQL 결과 표현](https://docs.hibernate.org/orm/6.6/querylanguage/html_single/) · [Hibernate TupleTransformer](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/query/TupleTransformer.html)

## 5. 엔티티 조회

`EntityManager.find()`는 PK로 관리 엔티티를 읽고 같은 컨텍스트의 인스턴스를 재사용할 수 있다. `getReference()`는 상태 로드를 늦출 수 있는 참조를 제공하므로 기존 PK로 FK를 설정하는 데 쓸 수 있다. 참조의 상태를 읽으면 조회가 발생할 수 있고, 없는 ID에 대한 오류가 접근 시점에 드러날 수 있다. 속성 변경과 생명주기가 필요하면 엔티티를 조회하고, 읽기 전용 화면에서 일부 컬럼만 필요하면 DTO를 고려한다. [Jakarta Persistence 3.1 §3.2 및 EntityManager API](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 6. 연관관계 로딩과 N+1

목록 조회 후 각 주문의 고객을 읽을 때 보조 SELECT가 반복되면 N+1이 된다. 요청에서 필요한 to-one은 fetch join이나 entity graph로 미리 가져오고, 지연 로딩이 필요하면 batch fetch로 여러 참조를 한 조회에서 초기화할 수 있다. 페치 여부를 검증할 때 최종 DTO에 필요한 속성까지 접근해 쿼리 수를 센다. [Hibernate 페치 전략](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)

to-many fetch join은 자식 수에 따라 SQL 결과 행을 늘린다. 부모 페이지가 필요하면 정렬된 부모 ID만 먼저 제한하고, 해당 ID들의 관계를 두 번째 쿼리에서 가져온 뒤 첫 조회 순서로 조립한다. 조회 사이의 스냅샷 일관성이 요구되면 DB 격리 수준도 함께 정한다. [Hibernate HQL 연관관계 fetch join](https://docs.hibernate.org/orm/6.6/querylanguage/html_single/)
