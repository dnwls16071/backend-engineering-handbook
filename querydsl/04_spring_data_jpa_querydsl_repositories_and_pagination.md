# Spring Data JPA Querydsl Repositories and Pagination

Spring Data JPA의 `JpaRepository`로 기본 저장·조회를 처리하고, DTO 검색처럼 별도 쿼리가 필요한 기능은 리포지토리 프래그먼트로 추가한다. 아래 예제는 [03번 문서](03_querydsl_repositories_with_plain_jpa.md)의 `TaskRow`, `TaskSearchCondition`, `TaskFilters`를 사용한다.

## 1. 프래그먼트 인터페이스와 구현 클래스

다음 인터페이스를 각각 같은 이름의 파일에 둔다.

```java
public interface TaskSearchRepository {
    Page<TaskRow> searchPage(TaskSearchCondition condition, Pageable pageable);
}
```

```java
public interface TaskRepository extends JpaRepository<Task, Long>, TaskSearchRepository {}
```

`TaskSearchRepositoryImpl`은 프래그먼트 이름인 `TaskSearchRepository` 뒤에 기본 접미사인 `Impl`을 붙인 것이다. 이 구현을 리포지토리 스캔 범위에 두면 `TaskRepository`로 기본 CRUD와 `searchPage()`를 함께 사용할 수 있다.

## 2. 내용과 카운트 쿼리 나누기

```java
@Transactional(readOnly = true)
public class TaskSearchRepositoryImpl implements TaskSearchRepository {
    private final JPAQueryFactory queryFactory;
    private final QTask task = QTask.task;
    private final QProject project = QProject.project;

    public TaskSearchRepositoryImpl(EntityManager entityManager) {
        this.queryFactory = new JPAQueryFactory(entityManager);
    }

    @Override
    public Page<TaskRow> searchPage(TaskSearchCondition condition, Pageable pageable) {
        BooleanExpression[] filters = TaskFilters.matching(condition);

        JPAQuery<TaskRow> contentQuery = queryFactory
            .select(Projections.constructor(TaskRow.class,
                task.id, task.title, project.name, task.priority))
            .from(task)
            .leftJoin(task.project, project)
            .where(filters);
        applySort(contentQuery, pageable.getSort());

        if (pageable.isPaged()) {
            contentQuery.offset(pageable.getOffset()).limit(pageable.getPageSize());
        }
        List<TaskRow> content = contentQuery.fetch();

        JPAQuery<Long> countQuery = queryFactory
            .select(task.id.count())
            .from(task)
            .leftJoin(task.project, project)
            .where(filters);

        return PageableExecutionUtils.getPage(content, pageable, countQuery::fetchOne);
    }

    private void applySort(JPAQuery<?> query, Sort sort) {
        for (Sort.Order order : sort) {
            boolean ascending = order.isAscending();
            OrderSpecifier<?> specifier = switch (order.getProperty()) {
                case "priority" -> ascending ? task.priority.asc() : task.priority.desc();
                case "title" -> ascending ? task.title.asc() : task.title.desc();
                case "id" -> ascending ? task.id.asc() : task.id.desc();
                default -> throw new IllegalArgumentException(
                    "Unsupported sort field: " + order.getProperty()
                );
            };
            query.orderBy(specifier);
        }
        if (sort.getOrderFor("id") == null) {
            query.orderBy(task.id.asc());
        }
    }
}
```

`PageableExecutionUtils`는 `org.springframework.data.support`에서 가져온다. 첫 페이지가 페이지 크기보다 작거나, 다음 페이지에서 일부 결과만 있어 끝을 확인할 수 있는 경우에는 내용 개수와 오프셋으로 전체 건수를 계산한다. 범위를 벗어난 빈 페이지처럼 내용만으로 전체 건수를 추론하기 어려우면 카운트 쿼리를 실행할 수 있다.

페이징 결과의 `totalElements`는 현재 페이지에 들어 있는 행 수와 다르다. 데이터와 카운트 쿼리는 같은 검색 범위를 표현해야 한다. 다대일 조인이 출력에만 필요하면 카운트에서 뺄 수 있다. 일대다 조인으로 루트 행이 늘어나는 쿼리는 무엇을 한 건으로 셀지 먼저 정하고, 필요하면 `countDistinct()` 또는 별도의 집계 쿼리를 사용한다.

## 3. 요청의 페이징과 정렬

`GET /tasks?page=0&size=20&sort=priority,desc`는 첫 페이지에 최대 20개 결과를 요청한다. Spring MVC에서 받은 `Pageable`을 전달하면 예제의 정렬 허용 목록이 필드 이름을 타입이 정해진 경로로 변환한다. `id`를 마지막 정렬 기준으로 추가하면 우선순위가 같은 작업도 순서가 정해진다.

예제는 필드와 오름차순·내림차순을 지원한다. 연관 엔티티 필드, 대소문자 구분, NULL 순서를 API로 제공한다면 허용 조건과 동작을 명시해 매핑한다. 전체 건수가 필요 없는 API에는 `Slice`로 다음 페이지가 있는지만 응답하는 방식도 선택할 수 있다.
