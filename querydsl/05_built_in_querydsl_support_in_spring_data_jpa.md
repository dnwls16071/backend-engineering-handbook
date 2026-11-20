# Built-In Querydsl Support in Spring Data JPA

Spring Data JPA는 Querydsl 조건을 받는 리포지토리 인터페이스와 웹 바인딩 도구를 제공한다. 요청 조건만 달라지는 엔티티 조회에는 이 기능을 사용할 수 있다. 조회 대상, 조인, DTO, 집계 쿼리 구조까지 제어해야 하는 경우에는 리포지토리 프래그먼트에서 `JPAQueryFactory`로 직접 작성할 수 있다.

## 1. QuerydslPredicateExecutor

```java
public interface TaskRepository extends JpaRepository<Task, Long>,
        TaskSearchRepository, QuerydslPredicateExecutor<Task> {}
```

위 코드는 [04번 문서](04_spring_data_jpa_querydsl_repositories_and_pagination.md)의 `TaskRepository`에 실행기 인터페이스를 추가한 형태다. `findOne()`, `findAll()`, `count()`, `exists()`에 Querydsl `Predicate`를 전달할 수 있다. [Spring Data JPA 3.5 · QuerydslPredicateExecutor](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/core-extensions.html#core.extensions.querydsl)

```java
QTask task = QTask.task;
Predicate pending = task.completed.isFalse().and(task.priority.goe(3));
Page<Task> page = taskRepository.findAll(
    pending, PageRequest.of(0, 20, Sort.by("id"))
);
```

기본 `findAll(Predicate, Pageable)`은 엔티티 페이지를 반환한다. 조건은 조합할 수 있고, 이 호출에서는 `LEFT JOIN`, 페치 조인, 임의의 `SELECT` 목록을 직접 정의할 수 없다. 연관 경로 접근이 묵시적 조인을 일으킬 수 있으므로, 관계가 없는 행도 포함해야 하는 조회는 생성 SQL을 확인한다.

## 2. Querydsl Web 바인딩

Spring Data Web 지원을 활성화한 MVC 컨트롤러에서는 `@QuerydslPredicate(root = Task.class) Predicate predicate`를 인자로 받을 수 있다. `?title=plan` 같은 쿼리 문자열을 조건식으로 바꾼다. 검색 가능 필드와 문자열 비교 방식은 `QuerydslBinderCustomizer`에서 지정할 수 있다. [Spring Data JPA 3.5 · Querydsl Web 바인딩](https://docs.spring.io/spring-data/jpa/reference/3.5/repositories/core-extensions.html#core.web.type-safe)

`TaskRepository`가 `QuerydslBinderCustomizer<QTask>`를 상속하도록 추가하고, 그 안에 `customize()`를 구현한다.

```java
public interface TaskRepository extends JpaRepository<Task, Long>,
        TaskSearchRepository, QuerydslPredicateExecutor<Task>,
        QuerydslBinderCustomizer<QTask> {

    @Override
    default void customize(QuerydslBindings bindings, QTask task) {
        bindings.excludeUnlistedProperties(true);
        bindings.including(task.title, task.priority);
        bindings.bind(task.title)
            .first((path, value) -> path.containsIgnoreCase(value));
    }
}
```

이 설정에서는 `title`과 `priority`를 검색 필드로 받는다. 검색 필드를 지정하는 정책과 사용자가 실제로 볼 수 있는 행을 정하는 접근 정책은 별개다. 사용자나 테넌트에 따른 접근 조건은 서버에서 기본 조건으로 적용한다.

## 3. QuerydslRepositorySupport와 직접 구성

| 방식 | 제공하는 기능 | 적합한 상황 |
| --- | --- | --- |
| `QuerydslPredicateExecutor` | 조건식 기반 조회·카운트·존재 확인과 페이징 | 엔티티의 필드 조건이 주로 바뀌는 조회 |
| `Querydsl Web` | URL 쿼리 파라미터를 Querydsl 조건으로 변환 | 제한된 필드를 바인딩해 검색을 제공하는 MVC API |
| `QuerydslRepositorySupport` | `EntityManager`, `from()`과 `Querydsl.applyPagination()` 사용 | 기존 리포지토리에 기반 클래스가 이미 사용되는 경우 |
| `JPAQueryFactory`를 사용하는 프래그먼트 | 조회 열, 조인, 정렬, 카운트 쿼리를 명시 | DTO 조회나 관계·집계가 있는 조회 |

`QuerydslRepositorySupport`는 기반 클래스에서 `EntityManager`와 페이징 보조 API를 제공한다. `applyPagination()`은 `Pageable`의 오프셋, 크기와 정렬을 쿼리에 반영한다. 계산식이나 여러 연관 경로를 정렬에 사용한다면, 조회에 맞는 Q 경로와 정렬식을 직접 매핑할 수 있다. [Spring Data JPA 3.5 · QuerydslRepositorySupport](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/support/QuerydslRepositorySupport.html) · [Spring Data JPA 3.5 · 페이징 적용 API](https://docs.spring.io/spring-data/jpa/reference/3.5/api/java/org/springframework/data/jpa/repository/support/Querydsl.html)

여러 프래그먼트에서 페이징 조립 코드가 반복되면 공통 지원 메서드를 만들 수 있다. 데이터 쿼리와 카운트 쿼리는 호출하는 쪽에서 각각 전달하도록 두면 조회별 범위와 집계를 검토하기 쉽다.
