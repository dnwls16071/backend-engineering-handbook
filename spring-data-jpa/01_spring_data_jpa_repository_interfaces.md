# Spring Data JPA Repository Interfaces

Spring Data JPA는 엔티티와 식별자 타입을 선언한 리포지토리 인터페이스에서 구현체를 생성한다. 기본 CRUD는 `JpaRepository`로 사용하고, 조회 조건이나 매핑을 더 직접 제어해야 하는 곳에서는 `EntityManager`를 사용할 수 있다. 예제는 **Java 17, Spring Boot 3.5, Spring Data JPA 3.5** 기준이다. [Spring Data JPA · 리포지토리 인터페이스 정의](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/definition.html)

## 1. 엔티티와 리포지토리 선언

아래 `Ticket`은 제목, 상태, 우선순위를 가진다. `TicketState`는 `OPEN`, `CLOSED`를 가진 enum이다. 두 타입과 리포지토리는 각각 같은 이름의 파일에 둔다.

```java
@Entity
@Table(name = "tickets")
public class Ticket {
    @Id
    @GeneratedValue
    private Long id;

    @Column(nullable = false)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TicketState state;

    @Column(nullable = false)
    private Integer priority;

    protected Ticket() {}

    public Ticket(String title, TicketState state, Integer priority) {
        this.title = title;
        this.state = state;
        this.priority = priority;
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public TicketState getState() {
        return state;
    }

    public Integer getPriority() {
        return priority;
    }

    public void rename(String title) {
        this.title = title;
    }
}
```

```java
public interface TicketRepository extends JpaRepository<Ticket, Long> {}
```

`JpaRepository<Ticket, Long>`의 두 타입 인수는 엔티티와 기본 키의 타입이다. Spring Boot의 기본 자동 설정에서는 애플리케이션 클래스의 패키지와 하위 패키지에서 리포지토리를 탐색한다. 패키지를 분리했다면 `@EnableJpaRepositories`로 리포지토리 스캔 범위를 지정할 수 있다. [Spring Boot 3.5 · JPA 리포지토리](https://docs.spring.io/spring-boot/3.5/reference/data/sql.html#data.sql.jpa-and-spring-data.repositories) · [Spring Data JPA · 리포지토리 생성](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/create-instances.html)

## 2. 직접 구현하는 경우와 비교

| 작업 | EntityManager | JpaRepository |
| --- | --- | --- |
| 저장 | `persist(entity)` | `save(entity)` |
| 기본 키로 조회 | `find(Ticket.class, id)` | `findById(id)` |
| 존재 확인·건수 | JPQL 등으로 조회 | `existsById(id)`, `count()` |
| 여러 건 조회 | JPQL과 정렬·범위 설정 | `findAll()`, `findAll(Sort)`, `findAll(Pageable)` |
| 관리 중인 객체 수정 | 트랜잭션 안에서 필드 변경 | 트랜잭션 안에서 조회한 뒤 필드 변경 |
| 삭제 | `remove(managedEntity)` | `delete(entity)`, `deleteById(id)` |

`findById()`는 대상이 없으면 `Optional.empty()`를 반환한다. `getReferenceById()`는 엔티티 참조를 반환하며, 대상이 없어도 상태에 처음 접근하기 전까지 오류가 미뤄질 수 있다. `save()`는 새 엔티티 판별 결과에 따라 `persist()` 또는 `merge()`를 사용한다. 병합이 일어날 수 있는 경로에서는 반환 객체를 이어서 사용한다. [Spring Data JPA 3.5 · JpaRepository API](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/JpaRepository.html) · [Spring Data JPA 3.5 · 엔티티 저장](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/entity-persistence.html)

## 3. 공통 인터페이스가 제공하는 범위

`Repository`는 엔티티 타입을 지정하는 기반 인터페이스다. `CrudRepository`는 공통 CRUD를, `ListCrudRepository`는 일부 결과를 `List`로 받는 CRUD를 제공한다. 페이징·정렬 인터페이스와 CRUD 인터페이스는 각각 선택할 수 있고, `JpaRepository`는 두 계열과 플러시 등 JPA 전용 기능을 함께 제공한다. [Spring Data JPA 3.5 · 리포지토리 인터페이스 선택](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/definition.html)

읽고 변경하는 과정은 서비스의 한 트랜잭션에 묶는다. 조회한 `Ticket`이 영속 상태라면 `rename()`을 호출한 변경은 플러시 때 감지된다. 일괄 삭제 메서드는 쿼리 한 번으로 행을 제거할 수 있으며, 이미 로딩한 엔티티의 상태와 DB가 달라질 수 있다. [Spring Data JPA 3.5 · 트랜잭션](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/transactions.html) · [Jakarta Persistence 3.1 · DB 동기화](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a1955)
