# Querydsl Repositories with Plain JPA

순수 JPA 리포지토리는 `EntityManager`로 엔티티를 저장하고, `JPAQueryFactory`로 검색 쿼리를 구성할 수 있다. 예제는 작업 검색 조건과 화면에 표시할 작업 행을 분리한다. [기본 엔티티 모델](01_querydsl_jpa_fundamentals.md)을 사용한다.

## 1. EntityManager를 사용하는 리포지토리

검색에 사용할 두 레코드를 각각 같은 이름의 파일에 둔다.

```java
public record TaskSearchCondition(String title, String projectName,
                                  Integer minPriority, Integer maxPriority) {}
```

```java
public record TaskRow(Long id, String title, String projectName, Integer priority) {}
```

리포지토리는 주입받은 트랜잭션 연동 `EntityManager`로 저장과 검색을 처리한다. 스프링 빈은 공유 프록시를 주입받고, 실제 영속성 컨텍스트는 트랜잭션 범위에서 사용한다. [Spring Framework 6.2 · 공유 EntityManager](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/orm/jpa/SharedEntityManagerCreator.html) · [Querydsl 5.0 · EntityManager를 사용하는 JPAQueryFactory](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/JPAQueryFactory.java)

```java
@Repository
@Transactional(readOnly = true)
public class TaskQueryRepository {
    private final EntityManager entityManager;
    private final JPAQueryFactory queryFactory;
    private final QTask task = QTask.task;
    private final QProject project = QProject.project;

    public TaskQueryRepository(EntityManager entityManager) {
        this.entityManager = entityManager;
        this.queryFactory = new JPAQueryFactory(entityManager);
    }

    @Transactional
    public void save(Task entity) {
        entityManager.persist(entity);
    }

    public Optional<Task> findById(Long id) {
        return Optional.ofNullable(entityManager.find(Task.class, id));
    }

    public List<TaskRow> search(TaskSearchCondition condition) {
        return queryFactory
            .select(Projections.constructor(TaskRow.class,
                task.id, task.title, project.name, task.priority))
            .from(task)
            .leftJoin(task.project, project)
            .where(TaskFilters.matching(condition))
            .orderBy(task.id.asc())
            .fetch();
    }
}
```

## 2. 검색 조건을 재사용 가능한 표현식으로 만들기

리포지토리와 같은 패키지에 조건을 모아 둔다. 이렇게 반환한 배열은 [04번 페이징 조회](04_spring_data_jpa_querydsl_repositories_and_pagination.md)의 데이터 쿼리와 카운트 쿼리에서도 사용할 수 있다.

```java
final class TaskFilters {
    private TaskFilters() {}

    static BooleanExpression[] matching(TaskSearchCondition condition) {
        QTask task = QTask.task;
        QProject project = QProject.project;
        return new BooleanExpression[] {
            hasText(condition.title()) ? task.title.containsIgnoreCase(condition.title()) : null,
            hasText(condition.projectName()) ? project.name.eq(condition.projectName()) : null,
            condition.minPriority() == null ? null : task.priority.goe(condition.minPriority()),
            condition.maxPriority() == null ? null : task.priority.loe(condition.maxPriority())
        };
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
```

`minPriority`와 `maxPriority`를 함께 받는 API라면 하한이 상한보다 큰 요청을 조회 전에 검증한다. 프로젝트 조건이 없으면 LEFT JOIN이 프로젝트에 연결되지 않은 작업도 보존한다. 프로젝트 이름이 입력되면 해당 이름에 일치하는 작업만 반환한다. `TaskRow`로 직접 조회하므로 결과 행을 만드는 데 필요한 열을 명시할 수 있다. [Querydsl 5.0 · 생성자 프로젝션](https://github.com/querydsl/querydsl/blob/QUERYDSL_5_0_0/querydsl-core/src/main/java/com/querydsl/core/types/Projections.java)

## 3. 조회 API와 실행 확인

검색 API는 `GET /tasks?projectName=Platform&minPriority=3`처럼 요청을 받고, 입력을 `TaskSearchCondition`으로 변환해 리포지토리에 전달할 수 있다. 요청 조건과 응답 DTO를 분리하면 내부 연관관계를 API 형식에 그대로 노출할 필요가 줄어든다.

통합 테스트에서는 프로젝트가 있는 작업, 프로젝트가 없는 작업, 우선순위 범위 밖의 작업을 함께 저장한다. 빈 조건의 결과와 프로젝트·우선순위를 함께 지정한 결과를 비교한다. 빈 조건에서 모든 행이 조회될 수 있으므로, 데이터가 커지는 API에는 [페이지 단위 조회](04_spring_data_jpa_querydsl_repositories_and_pagination.md)를 적용한다.
