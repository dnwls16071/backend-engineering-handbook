# Advanced Querydsl Projections and Dynamic Queries

화면에 필요한 열만 조회하려면 프로젝션을 사용한다. 검색 조건이 입력에 따라 달라지면 자바에서 조건식을 조합한다. 아래 예제는 [작업과 프로젝트 모델](01_querydsl_jpa_fundamentals.md)을 사용한다.

## 1. 스칼라, 튜플, DTO 프로젝션

```java
List<String> titles = queryFactory.select(task.title).from(task).fetch();

List<Tuple> values = queryFactory
    .select(task.title, task.priority)
    .from(task)
    .fetch();
String title = values.get(0).get(task.title);
```

단일 값을 조회하면 경로의 타입을 그대로 받는다. 여러 값을 조합해 리포지토리 밖으로 넘길 때는 각 값의 역할을 이름으로 표현한 DTO가 편하다. 위 튜플 예제는 데이터가 한 건 이상 있다고 가정한다.

| 방식 | DTO에 값을 넣는 방법 | 확인할 부분 |
| --- | --- | --- |
| `Projections.bean()` | 기본 생성자로 만든 객체의 setter 호출 | 프로퍼티와 선택 표현식의 이름 |
| `Projections.fields()` | 기본 생성자로 만든 객체의 필드에 직접 설정 | 필드와 선택 표현식의 이름 |
| `Projections.constructor()` | 인자 순서대로 생성자 호출 | 생성자 인수의 순서와 타입 |
| `@QueryProjection` | 생성된 Q 타입으로 DTO 생성자를 호출 | DTO 생성자에 어노테이션을 붙이고 빌드에서 Q 타입 생성 |

이름이 다르면 `task.title.as("label")`처럼 별칭을 부여한다. 생성자 프로젝션 예제에서는 `TaskSummary` 레코드의 컴포넌트 순서에 맞춰 조회한다.

```java
public record TaskSummary(Long id, String title) {}
```

```java
List<TaskSummary> summaries = queryFactory
    .select(Projections.constructor(TaskSummary.class, task.id, task.title))
    .from(task)
    .distinct()
    .fetch();
```

DTO 생성자에 `@QueryProjection`을 붙여 `QTaskSummary`를 생성하면 `select(new QTaskSummary(task.id, task.title))`로 조회할 수 있다. 이 방식은 타입이 다른 인자 전달을 컴파일 단계에서 확인한다. 같은 타입인 두 인자의 순서가 바뀌는 문제는 DTO와 쿼리의 의미를 대조해 검토한다.

## 2. 입력에 따라 달라지는 검색 조건

```java
BooleanBuilder filters = new BooleanBuilder();
if (titleParam != null && !titleParam.isBlank()) {
    filters.and(task.title.containsIgnoreCase(titleParam));
}
if (minPriority != null) {
    filters.and(task.priority.goe(minPriority));
}

List<Task> matches = queryFactory.selectFrom(task).where(filters).fetch();
```

`BooleanBuilder`는 조건을 단계별로 누적하는 데 편하다. 여러 조회에 같은 조건을 사용한다면 `BooleanExpression`을 반환하는 메서드로 옮기고 `where(titleContains(titleParam), priorityGoe(minPriority))`처럼 전달한다. Querydsl은 `where`에 전달된 `null`을 건너뛴다. 직접 `and()`를 호출해 조합할 때는 메서드 호출의 왼쪽 값이 `null`일 수 있는지 확인한다.

## 3. 일괄 갱신과 삭제

```java
entityManager.flush();
long changed = queryFactory
    .update(task)
    .set(task.priority, task.priority.add(1))
    .where(task.completed.isFalse())
    .execute();
entityManager.clear();
```

벌크 작업은 쓰기 트랜잭션에서 실행한다. 엔티티를 건별로 바꾸는 대신 DB에서 여러 행을 직접 수정한다. 실행 전 `flush()`로 대기 중인 변경을 반영하고 실행 후 `clear()`로 이전 상태를 가진 관리 엔티티를 분리한다. 같은 방식으로 `delete(task).where(...).execute()`를 실행할 수 있으며, 수정·삭제 범위를 확인해야 한다.

## 4. 함수 호출

`lower()`와 `concat()`처럼 제공되는 표현식은 메서드로 조합한다. DB 함수가 필요하면 `Expressions.stringTemplate("function('replace', {0}, {1}, {2})", task.title, "draft", "ready")`처럼 함수와 인자를 분리한다. 함수 처리와 반환 타입은 JPA 구현체 및 DB의 지원 범위를 확인한다.
