# Querydsl 5 Configuration for Spring Boot

Spring Boot 3.x의 JPA는 `jakarta.persistence`를 사용한다. Querydsl 5.0을 사용할 때는 런타임의 JPA 라이브러리와 빌드 단계의 어노테이션 프로세서를 모두 Jakarta 환경에 맞춘다.

## 1. Spring Boot 3.x와 Gradle 연결

아래 예제는 Spring Boot 3.x와 `io.spring.dependency-management` 플러그인이 적용된 Java 프로젝트의 `build.gradle`에 추가한다. Java 17 이상을 사용한다. `querydsl.version`을 지정하면 Spring Boot가 관리하는 Querydsl 모듈도 지정한 버전에 맞춰진다.

```groovy
def querydslVersion = '5.0.0'
ext['querydsl.version'] = querydslVersion

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation "com.querydsl:querydsl-jpa:${querydslVersion}:jakarta"

    annotationProcessor "com.querydsl:querydsl-apt:${querydslVersion}:jakarta"
    annotationProcessor 'jakarta.persistence:jakarta.persistence-api'
    annotationProcessor 'jakarta.annotation:jakarta.annotation-api'
}
```

```sh
./gradlew clean compileJava
```

기본 Gradle Java 소스 레이아웃이라면 `build/generated/sources/annotationProcessor/java/main`에서 `QTask.java` 같은 생성 파일을 확인할 수 있다. 엔티티를 바꾸면 다시 컴파일한다. 생성물이 없다면 엔티티의 `@Entity` import, APT의 `jakarta` 분류자, 프로세서 클래스패스의 JPA API를 함께 확인한다.

## 2. Spring Boot 2.6·2.7과 3.x 비교

| 환경 | 엔티티 import | `querydsl-jpa` 분류자 | `querydsl-apt` 분류자 |
| --- | --- | --- | --- |
| Spring Boot 2.6·2.7에서 Querydsl 5.0 사용 | `javax.persistence` | 분류자 없음 | `jpa` |
| Spring Boot 3.x에서 Querydsl 5.0 사용 | `jakarta.persistence` | `jakarta` | `jakarta` |

2.x 예제를 3.x로 옮길 때는 엔티티와 `EntityManager`의 import, JPA·APT 의존성을 같은 네임스페이스로 맞춘다. 이전 Q 타입을 빌드 디렉터리에서 지우고 다시 생성하면 의존성과 생성 코드가 일치하는지 확인할 수 있다.

## 3. PageableExecutionUtils 패키지

```java
import org.springframework.data.support.PageableExecutionUtils;
```

기존 예제의 `org.springframework.data.repository.support.PageableExecutionUtils` import를 위 패키지로 바꾼다. `getPage()`는 내용과 페이지 정보로 전체 건수를 계산할 수 있으면 카운트 실행을 생략한다. 검색 조건이 들어간 사용 예는 [04번 문서](04_spring_data_jpa_querydsl_repositories_and_pagination.md)에서 다룬다.

## 4. fetchResults()와 fetchCount() 전환

Querydsl 5.0의 JPA 쿼리에서는 `fetchResults()`와 `fetchCount()`가 deprecated 처리되어 있다. JPQL은 임의의 조회를 `FROM` 서브쿼리로 감싸 카운트하는 방식을 지원하지 않는다. 여러 `GROUP BY` 식이나 `HAVING`이 포함된 쿼리에서는 Querydsl이 결과를 메모리에 가져와 집계할 수 있다.

데이터는 `fetch()`로 가져오고, 건수는 같은 대상을 세는 쿼리에 집계식을 명시한다.

```java
List<Task> content = queryFactory
    .selectFrom(task)
    .where(task.completed.isFalse())
    .orderBy(task.id.asc())
    .offset(0)
    .limit(20)
    .fetch();

Long total = queryFactory
    .select(task.id.count())
    .from(task)
    .where(task.completed.isFalse())
    .fetchOne();
```

페이지에서 작업 수를 표시한다면 작업을 세고, 집계 화면에서 프로젝트 그룹 수를 표시한다면 조건을 충족한 그룹을 세는 쿼리를 작성한다. 조인이 있는 경우는 같은 작업이 여러 행으로 늘어나는지 확인한다.
