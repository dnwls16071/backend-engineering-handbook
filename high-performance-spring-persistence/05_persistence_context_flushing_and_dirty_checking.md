# Persistence Context, Flushing, and Dirty Checking

영속성 컨텍스트는 엔티티의 식별자와 객체를 연결하고, 변경 내용을 데이터베이스와 동기화할 때까지 추적한다. 예제는 Spring Boot 3.5, Spring Data JPA 3.5, Hibernate ORM 6.6, Jakarta Persistence 3.1, PostgreSQL을 기준으로 한다.

## 1. 영속성 컨텍스트와 엔티티의 상태

같은 영속성 컨텍스트에서 같은 엔티티 타입과 기본 키를 조회하면 하나의 관리 인스턴스를 공유한다. 예를 들어 관리 상태인 `Member`를 같은 기본 키로 다시 `find()`하면 컨텍스트에 있는 객체를 돌려준다. 엔티티의 상태에 따라 변경을 추적하는 범위가 달라진다. [Jakarta Persistence 3.1 · Entity Instance's Life Cycle](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

| 상태 | 전환과 동작 |
| --- | --- |
| 비영속(new) | `new Member(...)`로 생성한 객체다. `persist()`를 호출하면 관리 상태가 된다. |
| 관리(managed) | `find()`로 로드하거나 `persist()`로 등록한 객체다. 변경 내용을 플러시 때 반영한다. |
| 준영속(detached) | `detach()`, `clear()`, 컨텍스트 종료 등으로 관리 대상에서 제외된 객체다. 이후 필드 변경은 객체에만 남는다. |
| 삭제 예정(removed) | `remove()`로 등록한 객체다. 플러시하면 대응하는 행을 삭제한다. |

`flush()`는 대기 중인 변경을 현재 트랜잭션에서 SQL로 실행한다. 이후 트랜잭션을 롤백하면 그 DML도 취소된다. `clear()`는 컨텍스트의 엔티티를 모두 준영속 상태로 전환하므로, 반영해야 할 변경이 있으면 먼저 플러시한다. [Jakarta Persistence 3.1 · Synchronization to the Database](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 2. `AUTO`와 `COMMIT`에서 쿼리가 보는 값

JPA의 기본값인 `AUTO`에서는 트랜잭션에 참여 중인 컨텍스트의 변경이 쿼리 결과에 영향을 줄 수 있으면 제공자가 그 변경을 쿼리 처리에 반영해야 한다. `COMMIT`에서는 커밋 시 변경을 동기화하며, 커밋 전 쿼리가 대기 중인 변경을 볼지는 표준이 정하지 않는다. 쿼리의 `setFlushMode()`로 컨텍스트의 모드를 해당 쿼리에 한해 재정의할 수 있다. [Jakarta Persistence 3.1 · Queries and Flush Mode](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

Hibernate 6.6에서 `AUTO`로 JPQL/HQL을 실행하면 쿼리가 참조하는 테이블과 대기 중인 변경이 겹칠 때 플러시한다. 예를 들어 `Member`를 추가한 뒤 `select count(m) from Member m`을 실행하면 새 행이 집계에 포함된다. 두 엔티티의 매핑 테이블이 겹치지 않는다면 `AuditEvent`만 집계하는 JPQL은 그 INSERT를 앞당기지 않는다. 유효 모드가 `COMMIT`이면 JPQL/HQL 조회가 자동 플러시를 일으키지 않는다. [Hibernate ORM 6.6 · Flushing](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing)

Hibernate 6.6은 Spring Boot의 JPA 초기화 방식에서 동기화 대상이 지정되지 않은 네이티브 `SELECT`를 `AUTO`로 실행하면 먼저 플러시한다. 같은 `EntityManager`를 `Session`으로 언래핑해도 이 동작은 초기화 방식에 따른다. Hibernate 네이티브 방식으로 초기화하면 그런 쿼리는 `AUTO`에서도 자동 플러시를 건너뛴다. `addSynchronizedEntityClass(Member.class)` 등으로 대상 테이블을 알려주면 `AUTO`에서 변경과 테이블이 겹치는지 판단한다. 유효 모드가 `COMMIT`인 네이티브 `SELECT`도 쿼리 직전 자동 플러시를 건너뛴다. 모드와 무관하게 직전 변경을 SQL 조회에 반영해야 한다면 조회 전에 명시적으로 `flush()`한다. [Hibernate ORM 6.6 · NativeQueryImpl](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/query/sql/internal/NativeQueryImpl.java#L609-L648)

## 3. 삭제 후 삽입에서 발생하는 유니크 제약 위반

Hibernate 6.6의 `ActionQueue`는 작업 유형별로 실행 순서를 정한다. 같은 플러시에서 일반 엔티티 `INSERT`는 `EntityDeleteAction`보다 앞선다. 따라서 기존 회원을 `remove()`한 직후 같은 이메일로 새 회원을 `persist()`하면, PostgreSQL은 기존 행이 남아 있는 상태에서 새 행의 이메일에 대한 즉시 `UNIQUE` 제약을 검사한다. `orphanRemoval`이 예약하는 `OrphanRemovalAction`은 별도 유형이다. [Hibernate ORM 6.6 · Flush Operation Order](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing-order) · [PostgreSQL · Non-Deferred Uniqueness Constraints](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-COMPATIBILITY)

같은 회원의 이름만 바꾸는 작업이라면 기존 엔티티를 수정한다. 행을 교체해야 한다면 다음처럼 삭제를 먼저 플러시하고, 같은 트랜잭션에서 새 엔티티를 등록한다. 예제의 `Member`는 새 기본 키를 발급받고, `email`에는 즉시 검사하는 `UNIQUE` 제약이 있다. 이 플러시는 컨텍스트의 다른 대기 작업도 함께 처리한다. [Hibernate ORM 6.6 · Flushing](https://docs.hibernate.org/orm/6.6/userguide/html_single/#flushing)

```java
@Transactional
public void replaceMember(long oldId, String newName) {
    Member oldMember = members.findById(oldId).orElseThrow();
    String email = oldMember.getEmail();
    em.remove(oldMember);
    em.flush();
    em.persist(new Member(email, newName));
}
```

## 4. 관리 엔티티를 수정할 때 `save()` 생략하기

쓰기 트랜잭션에서 조회한 관리 엔티티는 도메인 메서드로 값을 변경하면 플러시 때 갱신된다. 여기서 `save()`를 호출하면 Spring Data JPA의 신규 여부 판정과, 기존 엔티티의 경우 `merge()` 경로가 추가된다. 관리 엔티티 자체는 그대로 유지되지만 `MERGE`가 설정된 연관관계로 전파될 수 있다. 준영속 엔티티를 병합해야 할 때는 `merge()`가 상태를 복사한 관리 인스턴스를 반환하므로 이후 수정에 그 반환값을 사용한다. [Spring Data JPA 3.5 · Persisting Entities](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html) · [Jakarta Persistence 3.1 · Merging Detached Entity State](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

```java
@Transactional
public void renameMember(long id, String newName) {
    Member member = members.findById(id).orElseThrow();
    member.rename(newName);
}

@Transactional
public void mergeAndRename(Member detached, String newName) {
    Member managed = em.merge(detached);
    managed.rename(newName);
}
```

## 5. 더티 체킹 비용과 벌크 DML 이후의 상태

Hibernate의 스냅샷 방식은 로드하거나 마지막으로 기록한 상태와 플러시 시점의 엔티티 상태를 비교한다. 관리하는 객체가 많을수록 스냅샷 메모리와 비교 비용이 늘 수 있다. 필요한 엔티티를 Hibernate 쿼리의 `setReadOnly(true)`로 새로 로드하면 해당 엔티티의 상태 스냅샷과 더티 체킹을 생략한다. 바이트코드 향상을 사용하면 엔티티가 변경된 속성을 직접 추적할 수 있다. `Date`처럼 객체 내부에서 상태가 바뀌는 타입은 필드 대입 없이 값이 바뀔 수 있으므로 실제 매핑에서 변경 감지 동작을 확인한다. [Hibernate ORM 6.6 · In-line Dirty Tracking](https://docs.hibernate.org/orm/6.6/userguide/html_single/#BytecodeEnhancement-dirty-tracking) · [Hibernate ORM 6.6 · Query.setReadOnly](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/query/Query.html#setReadOnly(boolean))

JPQL 벌크 `UPDATE`와 `DELETE`는 데이터베이스에 직접 적용되므로 이미 로드한 엔티티에 이전 값이 남을 수 있다. 같은 트랜잭션에서 관리 엔티티 변경과 벌크 작업을 섞을 때는 먼저 플러시해 대기 중인 변경을 보낸 뒤 벌크 DML을 실행하고, 컨텍스트를 비운 후 필요한 엔티티를 다시 조회한다. 벌크 `UPDATE`는 자동 낙관적 잠금 검사를 우회하므로 버전 검증이나 증가가 필요한 경우 쿼리에서 직접 처리한다. [Jakarta Persistence 3.1 · Bulk Update and Delete Operations](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

```java
@Transactional
public int deactivateInactiveMembers(Instant cutoff) {
    em.flush();
    int updated = em.createQuery("""
            update Member m set m.active = false
            where m.active = true and m.lastLoginAt < :cutoff
            """)
        .setParameter("cutoff", cutoff)
        .executeUpdate();
    em.clear();
    return updated;
}
```
