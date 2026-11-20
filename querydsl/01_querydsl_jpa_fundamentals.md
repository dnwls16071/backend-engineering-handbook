# Querydsl JPA Fundamentals

Querydsl JPA는 자바 표현식으로 JPQL 쿼리를 구성한다. 생성된 Q 타입으로 필드와 값의 자료형을 확인할 수 있고, 같은 조건을 여러 쿼리에서 재사용할 수 있다. 실행 시에는 JPA 구현체가 JPQL을 SQL로 번역한다. [Querydsl 5.0 · JPAQueryFactory](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/JPAQueryFactory.java)

이 문서의 예제는 **Java 17, Spring Boot 3.x, Querydsl 5.0**을 기준으로 한다. `Task`에는 `id`, `title`, `priority`, `completed`와 지연 로딩으로 설정한 선택적 다대일 관계 `project`가 있다. `Project`에는 `id`와 `name`이 있다. `QTask.task`와 `QProject.project`는 생성된 Q 타입의 기본 인스턴스다. Q 타입 생성은 [06번 문서](06_querydsl_5_configuration_for_spring_boot.md)에서 다룬다.

## 1. 조회 조건과 결과 타입

```java
JPAQueryFactory queryFactory = new JPAQueryFactory(entityManager);
QTask task = QTask.task;

List<Task> tasks = queryFactory
    .selectFrom(task)
    .where(task.completed.isFalse(), task.priority.goe(3))
    .orderBy(task.priority.desc(), task.id.asc())
    .offset(0)
    .limit(20)
    .fetch();
```

쉼표로 전달한 `where` 조건은 AND로 결합된다. `eq`, `in`, `between`, `contains`처럼 경로 타입에 맞는 비교를 사용할 수 있다. NULL을 찾는 조건은 `isNull()` 또는 `isNotNull()`으로 표현한다. 여러 행의 우선순위가 같을 수 있으므로 페이징 정렬에는 `id`처럼 순서를 확정할 수 있는 기준을 덧붙인다. [Querydsl 5.0 · 쿼리 조건 결합](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-core/src/main/java/com/querydsl/core/DefaultQueryMetadata.java)

| 조회 방식 | 결과 |
| --- | --- |
| `fetch()` | 여러 결과를 리스트로 반환하며, 결과가 없으면 빈 리스트다. |
| `fetchOne()` | 단일 결과를 반환한다. 결과가 없으면 `null`, 여러 개면 예외가 발생한다. |
| `fetchFirst()` | 조회를 한 건으로 제한한다. 어느 행이 첫 번째인지 중요하면 정렬을 명시한다. |
| `select(task.id.count()).from(task).fetchOne()` | 명시적인 집계식으로 전체 행 수를 조회한다. |

## 2. 연관관계 조인과 페치 조인

여러 표현식을 선택할 때는 `com.querydsl.core.Tuple`로 결과를 받는다.

```java
QProject project = QProject.project;

List<Tuple> matches = queryFactory
    .select(task.title, project.name)
    .from(task)
    .leftJoin(task.project, project)
    .on(project.name.eq("Platform"))
    .fetch();
```

위 쿼리는 모든 작업을 유지한다. 프로젝트가 없거나 이름이 `Platform`이 아닌 작업은 프로젝트 열이 `null`이다. 같은 비교를 `where`로 옮기면 해당 행들이 결과에서 제외된다. 일치하는 작업만 필요하면 `join(task.project, project)` 뒤에 조건을 적용할 수 있다.

연관관계가 없는 두 엔티티는 두 루트를 `from`에 두고 `where`로 비교할 수 있다. 여기에 외부 조인이 필요하면 JPA 구현체와 버전이 엔티티 조인 문법을 처리하는지 확인한다.

```java
List<Task> loaded = queryFactory
    .selectFrom(task)
    .leftJoin(task.project).fetchJoin()
    .where(task.completed.isFalse())
    .fetch();
```

페치 조인은 작업과 프로젝트를 같은 조회에서 로딩한다. 여러 작업의 지연 로딩 프로젝트에 접근하면서 추가 쿼리가 반복되는 상황에 쓸 수 있다. 컬렉션 페치 조인은 루트 행을 늘릴 수 있으므로 `offset`·`limit`와 함께 쓸 때 생성된 SQL과 결과 범위를 확인해야 한다. [Querydsl 5.0 · fetchJoin()](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/JPAQueryBase.java) · [Hibernate 6.6 · 페치 조인과 페이징](https://docs.hibernate.org/orm/6.6/querylanguage/html_single/#explicit-fetch-join)

## 3. 집계, 서브쿼리, 조건식

```java
var taskCount = task.id.count();
List<Tuple> counts = queryFactory
    .select(project.name, taskCount)
    .from(task)
    .join(task.project, project)
    .groupBy(project.id, project.name)
    .having(taskCount.goe(2L))
    .fetch();

QTask other = new QTask("other");
List<Task> highestPriority = queryFactory
    .selectFrom(task)
    .where(task.priority.eq(
        JPAExpressions.select(other.priority.max()).from(other)
    ))
    .fetch();
```

`where`는 집계 전 행을, `having`은 집계 후 그룹을 줄인다. 서브쿼리에 같은 엔티티를 다시 사용하면 별도 별칭을 준다. `JPAExpressions`로 `IN`이나 `EXISTS` 조건도 구성할 수 있다. JPQL에서 서브쿼리를 둘 수 있는 위치에는 제약이 있으므로, `SELECT` 등에서 사용하려면 구현체 지원 범위를 확인한다. [Querydsl 5.0 · JPAExpressions](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/JPAExpressions.java) · [Jakarta Persistence 3.1 · JPQL 서브쿼리](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a5196)

`CaseBuilder`는 진행 중인 작업에 0, 완료 작업에 1을 부여하는 등 조건부 값을 만든다. `new CaseBuilder().when(task.completed.isFalse()).then(0).otherwise(1)`을 변수에 두면 `select`와 `orderBy`에서 공유할 수 있다.

`task.title.concat("-").concat(task.priority.stringValue())`는 제목과 우선순위를 문자열로 연결한다. 조회 결과에 고정된 값을 넣을 때는 `Expressions.constant("TASK")`를 사용할 수 있다.
