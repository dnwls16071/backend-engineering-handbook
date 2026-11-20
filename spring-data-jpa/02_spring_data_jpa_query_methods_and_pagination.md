# Spring Data JPA Query Methods and Pagination

엔티티를 찾는 간단한 조건은 메서드 이름으로 표현할 수 있다. 조회 열이나 조인을 제어해야 하면 JPQL을 명시한다. 예제는 [01번의 Ticket 모델](01_spring_data_jpa_repository_interfaces.md)을 사용한다. [Spring Data JPA 3.5 · 쿼리 메서드](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html)

## 1. 파생 쿼리, NamedQuery, @Query

| 방식 | 예 | 동작 |
| --- | --- | --- |
| 메서드 이름으로 파생 | `findByStateAndPriorityGreaterThan(...)` | 엔티티 속성명과 비교 키워드를 해석한다. |
| NamedQuery 사용 | `Ticket.findOpenTickets` | 엔티티명과 메서드명을 조합한 이름으로 등록된 쿼리를 찾는다. |
| `@Query`로 선언 | 리포지토리 메서드에 JPQL 명시 | 같은 메서드에 대응하는 NamedQuery보다 우선한다. |

이 문서의 `@Query`와 `@EntityGraph`는 `org.springframework.data.jpa.repository` 패키지에서 가져온다.

```java
List<Ticket> findTop10ByStateOrderByPriorityDescIdAsc(TicketState state);

@Query("""
    select new example.ticket.TicketSummary(t.id, t.title)
    from Ticket t
    where t.state = :state
    order by t.id
    """)
List<TicketSummary> findSummaries(@Param("state") TicketState state);
```

`TicketSummary`는 `example.ticket` 패키지의 `public record TicketSummary(Long id, String title) {}`로 선언할 수 있다. 이름 기반 파라미터는 `@Param`과 JPQL의 `:state`처럼 같은 이름으로 지정한다. `List<T>`는 결과가 없으면 빈 리스트를 받는다. `Optional<T>`는 결과가 없으면 빈 값을 받으며, 단건을 기대한 메서드에 여러 행이 일치하면 예외가 발생한다. [Spring Data JPA 3.5 · 쿼리 메서드](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html) · [Spring Data JPA 3.5 · 반환 타입](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/query-return-types-reference.html)

## 2. Page, Slice, List 선택

| 반환 타입 | 제공하는 정보 | 실행 비용 |
| --- | --- | --- |
| `Page<T>` | 현재 내용, 전체 건수와 페이지 수 | 필요하면 카운트 쿼리 실행 |
| `Slice<T>` | 현재 내용과 다음 페이지 존재 여부 | 보통 페이지 크기보다 한 행 더 조회 |
| `List<T>`와 `Pageable` | 해당 범위의 내용 | 페이지 메타데이터와 전체 건수 계산 없음 |

```java
@Query(
    value = "select t from Ticket t where t.state = :state",
    countQuery = "select count(t) from Ticket t where t.state = :state"
)
Page<Ticket> findPageByState(@Param("state") TicketState state, Pageable pageable);
```

`PageRequest.of(0, 20, Sort.by(Sort.Order.desc("priority"), Sort.Order.asc("id")))`는 첫 페이지의 정렬과 범위를 지정한다. 우선순위가 같은 경우 `id`가 순서를 결정한다. 내용과 카운트 쿼리는 동일한 검색 범위를 표현해야 하며, 카운트에 필요 없는 로딩 전용 조인은 뺄 수 있다. [Spring Data JPA 3.5 · 페이징과 정렬](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/query-methods-details.html) · [Spring Data JPA 3.5 · countQuery](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/Query.html#countQuery())

## 3. 벌크 변경

```java
@Modifying(flushAutomatically = true, clearAutomatically = true)
@Query("update Ticket t set t.state = :target where t.state = :source")
int bulkTransition(@Param("source") TicketState source,
                   @Param("target") TicketState target);
```

서비스의 쓰기 트랜잭션 안에서 호출한다. `flushAutomatically`는 실행 전에 대기 중인 변경을 플러시하고, `clearAutomatically`는 실행 후 영속성 컨텍스트를 비운다. JPQL 벌크 변경은 DB 행을 직접 바꾸므로 이전에 읽은 엔티티 값이 자동으로 바뀌지 않는다. 메서드 이름으로 파생된 삭제는 대상 엔티티를 조회해 건별로 제거할 수 있으며, `@Modifying`을 붙인 벌크 삭제는 별도의 실행 경로를 사용한다. [Spring Data JPA 3.5 · 변경 쿼리](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html#jpa.modifying-queries) · [Spring Data JPA 3.5 · Modifying API](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/Modifying.html)

## 4. 로딩 범위, 힌트, 잠금

`Ticket`에 지연 로딩 `project` 연관관계가 있다면 다음 메서드로 조회 시 필요한 연관 범위를 지정할 수 있다. 조인 또는 추가 조회 방식은 매핑과 JPA 구현체에 따라 달라질 수 있으므로 실행 SQL을 확인한다. [Spring Data JPA 3.5 · 엔티티 그래프](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html#jpa.entity-graph)

일반 JPQL 조인은 다른 엔티티의 속성을 검색 조건이나 반환 값에 사용할 때 쓰인다. 반환된 엔티티의 연관관계도 조회 시점에 초기화해야 한다면 `JOIN FETCH`나 엔티티 그래프로 로딩 범위를 명시한다. [Jakarta Persistence 3.1 · 페치 조인](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a4931)

```java
@EntityGraph(attributePaths = "project")
List<Ticket> findAllByState(TicketState state);

@Lock(LockModeType.PESSIMISTIC_WRITE)
Optional<Ticket> findForUpdateById(Long id);
```

비관적 쓰기 잠금은 트랜잭션 안에서 사용하고, 잠금 충돌이 일어날 범위와 유지 시간을 확인한다. `@QueryHints`는 JPA 구현체에 조회 실행 힌트를 넘긴다. 페이지의 내용 쿼리에만 적용할 힌트라면 `forCounting = false`를 지정할 수 있다. [Spring Data JPA 3.5 · 잠금](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/locking.html) · [Spring Data JPA 3.5 · 쿼리 힌트](https://docs.spring.io/spring-data/jpa/reference/3.5/jpa/query-methods.html#jpa.query-hints)
