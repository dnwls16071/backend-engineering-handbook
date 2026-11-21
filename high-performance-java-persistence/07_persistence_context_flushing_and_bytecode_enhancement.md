# Persistence Context, Flushing, and Bytecode Enhancement

영속성 컨텍스트는 엔티티의 동일성을 유지하고 관리 중인 변경을 추적한다. 플러시는 추적된 변경을 DB와 동기화한다. 트랜잭션의 커밋과 롤백은 별도의 경계다. [Jakarta Persistence 3.1 §3.2](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate 플러시](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing)

## 1. 영속성 컨텍스트와 플러시

신규 인스턴스를 `persist()`하면 관리 상태가 되고, 열린 컨텍스트에서 조회한 객체의 필드를 변경하면 Hibernate가 플러시 시점에 반영할 수 있다. `detach()`와 `clear()`는 해당 인스턴스의 관리를 끊는다. 아직 플러시되지 않은 변경이 필요하다면 먼저 `flush()`한다. 플러시에서 제약 오류를 확인할 수 있지만 DB에서 커밋 시점까지 지연한 제약은 커밋까지 확인해야 한다.

## 2. ActionQueue와 SQL 순서

Hibernate의 `ActionQueue`는 예약한 작업을 유형별로 실행한다. 같은 플러시 안에서 기존 행에 `remove()`를 먼저 호출해도 새 행의 일반 INSERT가 기존 행의 일반 DELETE보다 앞설 수 있다. 두 행이 같은 즉시 UNIQUE 키를 사용하면 INSERT 시점에 위반이 발생할 수 있다. 가능한 경우 기존 엔티티의 값을 수정하는 방식으로 표현한다. 삭제 후 재생성이 필요한 경우 플러시를 사이에 두는 동작과 FK 제약을 함께 검증한다. [Hibernate 플러시 작업 순서](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing-order)

## 3. AUTO 플러시 모드

JPA `AUTO`는 활성 트랜잭션에 참여하는 컨텍스트의 변경 중 쿼리 결과에 영향을 줄 수 있는 변경이 쿼리에 보이도록 요구한다. Hibernate의 JPQL/HQL은 대기 중인 SQL 작업과 조회 대상 테이블이 겹치는지 판단한다. 예를 들어 관리 중인 주문 상태를 바꾼 다음 주문의 상태별 개수를 집계하면 집계 전에 변경이 플러시될 수 있다. [Jakarta Persistence 3.1 §3.10.8](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate AUTO 플러시](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing-auto)

Hibernate 6.6의 동기화 대상이 없는 네이티브 조회는 부트스트랩 방식에 따라 달라진다. JPA 방식에서는 AUTO가 조회 전에 플러시하고, 네이티브 Hibernate 방식에서는 건너뛸 수 있다. `NativeQuery.addSynchronizedEntityClass()`로 영향받는 엔티티를 선언하거나, 반드시 반영해야 하는 시점에 명시적으로 `flush()`한다. [Hibernate 6.6 네이티브 쿼리 구현](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/query/sql/internal/NativeQueryImpl.java)

## 4. 스냅샷 기반 변경 감지

Hibernate는 엔티티를 로드할 때의 상태를 보관하고 플러시에서 현재 값과 비교할 수 있다. 많은 엔티티를 장시간 관리하면 스냅샷과 플러시 비용이 늘 수 있다. 대량 쓰기에서는 일정 간격으로 `flush()`와 `clear()`를 적용하고, 읽기 화면에서는 필요한 컬럼만 투영하는 방법을 함께 검토한다. 변경 감지로 UPDATE 필요 여부를 판단하는 것과 UPDATE의 SET 절에 어떤 컬럼을 넣는지는 별개의 동작이다. [Hibernate 영속성 컨텍스트](https://docs.hibernate.org/orm/6.6/userguide/html_single/#pc) · [Hibernate 동적 갱신](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/annotations/DynamicUpdate.html)

## 5. 바이트코드 향상과 인라인 변경 추적

Hibernate는 빌드 시점에 엔티티 바이트코드를 향상해 변경한 속성 이름을 엔티티가 직접 추적하게 할 수 있다. Maven이나 Gradle의 enhancement 설정을 Hibernate ORM 버전에 맞춘다. 같은 영속성 컨텍스트 크기에서 플러시 시간과 UPDATE 수를 비교한다. 내부 상태만 바뀌는 가변 값은 필드 대입 없이 변경될 수 있으므로 해당 타입의 mutability 매핑과 실제 플러시 결과를 확인한다. [Hibernate 바이트코드 향상](https://docs.hibernate.org/orm/6.6/userguide/html_single/#BytecodeEnhancement) · [Hibernate 빌드 플러그인](https://docs.hibernate.org/orm/6.6/introduction/html_single/)
