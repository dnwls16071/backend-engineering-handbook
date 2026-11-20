# Spring Data JPA Repository Internals and Transactions

기본 리포지토리 동작은 `SimpleJpaRepository`가 구현한다. 트랜잭션 범위를 어디에 두는지와 `save()`가 새 객체를 어떻게 구별하는지를 알면, SQL이 언제 실행되고 어느 객체가 관리 상태인지 판단하기 쉽다. [Spring Data JPA 3.5 · SimpleJpaRepository](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/support/SimpleJpaRepository.html)

## 1. 리포지토리와 서비스의 트랜잭션 경계

| 호출 | 기본 동작 |
| --- | --- |
| 상속받은 CRUD 조회 메서드 | 읽기 전용 트랜잭션 설정 적용 |
| 상속받은 CRUD 쓰기 메서드 | 일반 쓰기 트랜잭션 설정 적용 |
| 새로 선언한 파생 쿼리나 `@Query` 메서드 | 별도 선언이 없으면 자체 트랜잭션 설정 없이 실행 |
| 서비스의 `@Transactional` 내부에서 호출 | 일반적인 전파 수준에서는 바깥 트랜잭션에 참여 |

여러 리포지토리를 함께 쓰거나 조회한 엔티티를 바꿀 때는 서비스가 전체 작업의 트랜잭션을 정한다. `readOnly = true`는 읽기 경로의 최적화 힌트다. Hibernate에서 플러시 방식이나 변경 감지 비용을 줄이는 데 쓰일 수 있다. 쓰기 차단이나 권한 검사는 별도로 적용한다. [Spring Data JPA 3.5 · 트랜잭션 기본값과 서비스 경계](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/transactions.html)

```java
@Transactional
public void renameTicket(Long id, String title) {
    Ticket ticket = ticketRepository.findById(id).orElseThrow();
    ticket.rename(title);
}
```

위 서비스 메서드에서 조회한 객체는 변경 감지의 대상이다. 트랜잭션이 완료될 때 수정 SQL이 반영된다. [Jakarta Persistence 3.1 · DB 동기화](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a1955)

## 2. save()가 persist()와 merge()를 선택하는 기준

| 상태 판별 | 새 엔티티 조건 |
| --- | --- |
| 래퍼 타입 `@Version` 속성이 있는 경우 | 버전이 `null` |
| 래퍼 타입 버전 속성이 없는 기본 경우 | 식별자가 `null` |
| `Persistable` 구현 | `isNew()`가 `true` |

새 엔티티는 `persist()` 후 넘긴 객체를 반환한다. 기존 엔티티로 판단하면 `merge()`의 반환 객체를 사용한다. 준영속 입력은 자기 Java 객체가 곧바로 관리 상태로 전환된다고 가정하면 안 된다. `saveAndFlush()`로 플러시를 요청할 수도 있으며, 커밋 여부는 바깥 트랜잭션에 달려 있다. [Spring Data JPA 3.5 · 저장과 새 엔티티 판별](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html) · [Jakarta Persistence 3.1 · 준영속 상태 병합](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#merging-detached-entity-state)

## 3. 식별자를 직접 지정하는 엔티티

객체를 만들 때 ID를 직접 부여하고 래퍼 버전 속성이 없다면, 새 객체도 기본 판별에서 기존 엔티티로 분류될 수 있다. 그런 모델에서는 `Persistable`로 상태를 명시할 수 있다. 아래 상위 클래스는 ID를 제공하는 엔티티에서 상속하고, 저장·로딩 이후에는 새 객체 플래그를 변경한다. [Spring Data JPA 3.5 · 직접 할당 ID와 Persistable](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html)

```java
@MappedSuperclass
public abstract class AssignedIdEntity<ID> implements Persistable<ID> {
    @Transient
    private boolean newEntity = true;

    @Override
    public boolean isNew() {
        return newEntity;
    }

    @PostPersist
    @PostLoad
    void markExisting() {
        newEntity = false;
    }
}
```

`newEntity`는 메모리에서만 사용하는 상태다. 필드 접근을 기준으로 한 예제이며, 하위 엔티티가 실제 ID와 `getId()`를 제공한다.
