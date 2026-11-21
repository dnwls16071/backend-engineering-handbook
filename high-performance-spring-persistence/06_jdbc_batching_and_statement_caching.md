# JDBC Batching and Statement Caching

JDBC 배치는 같은 SQL에 여러 파라미터 세트를 묶어 실행한다. Prepared statement 캐시는 같은 SQL을 반복해서 준비하는 비용을 줄인다. 예제는 Spring Boot 3.5, Spring Data JPA 3.5, Hibernate ORM 6.6, Jakarta Persistence 3.1, PostgreSQL과 pgJDBC를 기준으로 한다.

## 1. JDBC의 `addBatch()`와 `executeBatch()`

`PreparedStatement`에 값을 바인딩하고 `addBatch()`를 호출하면 현재 파라미터 세트가 배치에 들어간다. `executeBatch()`가 누적 작업을 실행하고 갱신 건수 배열을 반환한다. 드라이버와 프로토콜에 따라 개별 호출보다 네트워크 왕복이 줄어들 수 있다. 배치의 실행과 트랜잭션의 확정은 별도다. 일부 문장이 실행된 뒤 `BatchUpdateException`이 발생할 수 있으므로, 함께 성공해야 할 변경은 한 트랜잭션에 넣고 실패하면 롤백한다. [Java SE 21 · PreparedStatement](https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/PreparedStatement.html#addBatch()) · [Java SE 21 · Statement](https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/Statement.html#executeBatch())

다음은 직접 확보한 JDBC 커넥션에서 구독자 목록을 한 트랜잭션으로 추가하는 예다. `newsletter_recipient.email`에 중복을 제한하는 제약이 있다면 중복 삽입에서 실패한 배치 전체를 롤백한다. [Java SE 21 · Connection](https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/Connection.html#setAutoCommit(boolean))

```java
static void insertRecipients(DataSource dataSource, List<String> emails) throws SQLException {
    try (Connection connection = dataSource.getConnection()) {
        connection.setAutoCommit(false);
        try {
            try (PreparedStatement statement = connection.prepareStatement(
                    "insert into newsletter_recipient (email) values (?)")) {
                for (String email : emails) {
                    statement.setString(1, email);
                    statement.addBatch();
                }
                statement.executeBatch();
            }
            connection.commit();
        } catch (SQLException | RuntimeException failure) {
            try {
                connection.rollback();
            } catch (SQLException rollbackFailure) {
                failure.addSuppressed(rollbackFailure);
            }
            throw failure;
        }
    }
}
```

## 2. `saveAll()`과 Hibernate 배치 설정

Spring Data JPA의 `SimpleJpaRepository.saveAll()`은 하나의 트랜잭션에서 원소마다 `save()`를 호출한다. 실제 DML을 JDBC 배치로 실행할지는 Hibernate 설정과 매핑에 달려 있다. `hibernate.jdbc.batch_size` 기본값은 `0`이며, 양수로 지정하면 Hibernate가 한 배치에 모을 최대 문장 수를 정한다. Hibernate 6.6은 `GenerationType.IDENTITY` 엔티티의 삽입에서 INSERT를 실행해 식별자를 얻으므로 해당 INSERT를 배치에 넣지 않는다. PostgreSQL에서 시퀀스를 쓰는 `GenerationType.SEQUENCE`는 식별자를 INSERT 전에 얻을 수 있어 삽입 배치와 함께 쓸 수 있다. [Spring Data JPA 3.5 · SimpleJpaRepository](https://github.com/spring-projects/spring-data-jpa/blob/3.5.x/spring-data-jpa/src/main/java/org/springframework/data/jpa/repository/support/SimpleJpaRepository.java#L603-L639) · [Hibernate ORM 6.6 · Batching](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch)

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

대량 삽입에서 `saveAll()`은 입력을 순회하며 결과 목록을 만들고 영속성 컨텍스트에 엔티티를 쌓는다. `persist()` 루프에서 일정 건수마다 `flush()` 후 `clear()`하면 컨텍스트에 남는 관리 엔티티 수를 제한할 수 있다. 배치 크기와 플러시 간격, 트랜잭션의 커밋 간격은 각각 독립적으로 정한다. [Spring Boot 3.5 · Data Access](https://docs.spring.io/spring-boot/3.5/how-to/data-access.html) · [Hibernate ORM 6.6 · Batching](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch)

## 3. 연관관계 전파와 SQL 실행 순서

주문에서 항목으로 `CascadeType.PERSIST`를 설정하면 주문을 등록할 때 항목도 관리 상태가 된다. 주문 항목의 `order_id` 외래 키 때문에 같은 주문의 부모 행이 먼저 필요하다. 주문과 항목 INSERT가 번갈아 실행되면 서로 다른 SQL 템플릿으로 자주 전환되어 배치가 잘게 나뉜다. `hibernate.order_inserts`는 외래 키 의존성을 고려하면서 같은 엔티티 종류의 INSERT를 모으고, `hibernate.order_updates`는 UPDATE를 엔티티 종류와 기본 키 순서로 정렬한다. 별도 플러시에 걸친 작업은 함께 묶을 수 없고, 정렬 비용도 발생하므로 설정 전후의 배치 실행 횟수와 처리 시간을 비교한다. [Hibernate ORM 6.6 · ActionQueue](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/engine/spi/ActionQueue.java) · [Hibernate ORM 6.6 · Batching](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch)

## 4. `@DynamicUpdate`가 배치와 SQL 재사용에 미치는 영향

`@DynamicUpdate`는 수정된 속성에 맞춰 `UPDATE` SQL을 생성한다. 이름만 바꾼 회원과 이메일만 바꾼 회원을 갱신하면 서로 다른 SQL 템플릿이 된다. 한 `PreparedStatement`에 묶으려면 SQL 템플릿이 같아야 하고, Hibernate 6.6의 동적 갱신 실행 경로는 두 갱신의 SQL이 우연히 같더라도 배치 키를 부여하지 않는다. 갱신 열을 줄여 얻는 이점과 SQL 생성 및 배치 실행 비용을 실제 변경 패턴으로 비교한다. [Hibernate ORM 6.6 · DynamicUpdate](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/annotations/DynamicUpdate.html) · [Hibernate ORM 6.6 · UpdateCoordinatorStandard](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/persister/entity/mutation/UpdateCoordinatorStandard.java#L911-L978) · [Hibernate ORM 6.6 · AbstractMutationCoordinator](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/persister/entity/mutation/AbstractMutationCoordinator.java#L61-L72)

```sql
UPDATE app_member SET name = ? WHERE id = ?;
UPDATE app_member SET email = ? WHERE id = ?;
```

## 5. pgJDBC의 Prepared Statement 캐시와 Hibernate 쿼리 계획 캐시

Hibernate의 쿼리 계획 캐시는 `SessionFactory`에서 HQL/JPQL 해석과 쿼리 실행 계획 같은 ORM 내부 작업을 재사용한다. pgJDBC는 물리 커넥션마다 SQL 준비 정보를 캐시한다. 동일한 SQL과 호환되는 파라미터 타입으로 그 커넥션에서 반복 실행하면 `prepareThreshold`에 도달한 뒤 서버 측 prepared statement를 활용할 수 있다. 커넥션 풀 전체로 보면 같은 SQL도 각 물리 커넥션에서 별도로 사용 횟수를 쌓는다. [Hibernate ORM 6.6 · QueryInterpretationCache](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/query/spi/QueryInterpretationCache.html) · [pgJDBC · Server Prepared Statements](https://jdbc.postgresql.org/documentation/server-prepare/)

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/shop?prepareThreshold=5&preparedStatementCacheQueries=256&preparedStatementCacheSizeMiB=5
```

예시의 `5`, `256`, `5`는 각각 서버 측 준비를 시작할 실행 횟수, 물리 커넥션당 최대 캐시 쿼리 수와 최대 캐시 크기(MiB)의 기본값이다. 배치 INSERT에서 `reWriteBatchedInserts=true`를 사용하면 호환되는 INSERT를 여러 행의 `VALUES` 목록을 가진 문장으로 재작성할 수 있다. `hibernate-jfr`을 사용하는 환경에서는 `org.hibernate.orm.JdbcBatchExecution` 이벤트로 배치 실행을 확인할 수 있다. 서버 측 준비는 같은 PostgreSQL 세션에서 `pg_prepared_statements`를 조회해 확인한다. [pgJDBC · Connection Parameters](https://jdbc.postgresql.org/documentation/use/) · [Hibernate ORM 6.6 · Monitoring with Java Flight Recorder](https://docs.hibernate.org/orm/6.6/userguide/html_single/) · [PostgreSQL · pg_prepared_statements](https://www.postgresql.org/docs/current/view-pg-prepared-statements.html)
