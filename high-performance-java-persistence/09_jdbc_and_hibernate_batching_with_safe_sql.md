# JDBC and Hibernate Batching with Safe SQL

JDBC 배치는 같은 유형의 작업을 묶어 제출한다. 문장 수, 드라이버 호출 횟수, DB에서 실행된 작업 수를 각각 측정하면 어느 계층에서 비용이 줄었는지 판단할 수 있다. [Hibernate JDBC 배치](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch)

## 1. JDBC와 Hibernate의 배치 실행

다음 메서드는 호출자가 관리하는 트랜잭션에서 연결을 받아 재고 수량을 변경한다. 호출자가 커밋과 실패 시 롤백을 책임진다. 큰 입력은 일정 개수마다 `executeBatch()`로 제출하고 작업 전체를 한 트랜잭션으로 묶을지 별도로 결정한다.

```java
static int[] updateQuantities(Connection connection, Map<Long, Integer> quantities)
        throws SQLException {
    String sql = "update inventory set quantity = ? where id = ?";
    try (PreparedStatement statement = connection.prepareStatement(sql)) {
        for (var entry : quantities.entrySet()) {
            statement.setInt(1, entry.getValue());
            statement.setLong(2, entry.getKey());
            statement.addBatch();
        }
        return statement.executeBatch();
    }
}
```

반환 배열에는 항목별 갱신 수나 `SUCCESS_NO_INFO`가 들어갈 수 있고, 실패하면 `BatchUpdateException`에서 드라이버가 보고한 결과를 확인할 수 있다. Hibernate의 `hibernate.jdbc.batch_size`를 양수로 설정하면 호환되는 SQL을 플러시에서 묶는다. IDENTITY로 키를 생성하는 엔티티의 INSERT는 Hibernate에서 JDBC 배치 대상이 되지 않는다. [JDBC Statement API](https://docs.oracle.com/en/java/javase/17/docs/api/java.sql/java/sql/Statement.html#executeBatch()) · [Hibernate 세션 배치](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch-session-batch)

## 2. Cascade 작업과 배치 순서

부모를 `persist()`하면 `cascade=PERSIST`가 설정된 관계의 자식도 영속화할 수 있다. 부모·자식 INSERT가 번갈아 실행되면 같은 SQL이 모이는 구간이 짧아질 수 있다. `hibernate.order_inserts=true`는 Hibernate에 INSERT 정렬을 요청하며 FK 의존성과 식별자 전략에 따라 결과가 달라진다. 정렬 비용까지 포함해 처리량을 비교한다. [Hibernate 배치 설정](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch-session-batch)

## 3. 엔티티 UPDATE 배치와 벌크 갱신

일반 엔티티 UPDATE를 많이 실행할 때는 `hibernate.order_updates=true`가 호환되는 문장을 모으는 데 도움이 될 수 있다. `@DynamicUpdate`는 바뀐 컬럼으로 SQL을 구성한다. Hibernate ORM 6.6의 동적 UPDATE 경로는 JDBC 배치 키를 사용하지 않으므로 해당 환경의 배치 횟수를 확인한다. 관리 엔티티를 계속 쌓지 않도록 일정 간격으로 `flush()`와 `clear()`를 적용할 수 있다. `clear()` 뒤에는 다시 사용할 참조를 새로 얻는다. [Hibernate 6.6 UpdateCoordinatorStandard](https://github.com/hibernate/hibernate-orm/blob/6.6/hibernate-core/src/main/java/org/hibernate/persister/entity/mutation/UpdateCoordinatorStandard.java)

같은 조건으로 한 번에 값을 바꿀 수 있다면 JPQL 벌크 UPDATE도 가능하다. 벌크 갱신은 관리 객체의 상태나 일반적인 엔티티별 버전 검사를 자동으로 맞춰주지 않는다. 실행 전 필요한 변경을 플러시하고, 실행 후 컨텍스트를 비우거나 대상 행을 다시 읽는다. 버전 검사가 필요한 변경은 버전 조건과 영향을 받은 행 수를 명시적으로 검토한다. [Jakarta Persistence 3.1 §4.10](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 4. 파라미터 바인딩으로 SQL 인젝션 방지

외부 입력은 SQL이나 HQL 문자열에 이어 붙이지 않고 값 파라미터에 바인딩한다. 배치에서도 SQL 형태를 고정하고 매 항목의 값 전체를 설정한 뒤 `addBatch()`한다. 열 이름이나 정렬 방향은 값 파라미터로 바인딩할 수 없으므로, 공개한 선택값을 코드 안의 열과 방향 상수에 매핑한다. 예를 들어 정렬 키로 `NEWEST`와 `OLDEST`만 받고 그에 해당하는 정렬 표현식을 선택한다. [OWASP SQL 인젝션 예방 지침](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
