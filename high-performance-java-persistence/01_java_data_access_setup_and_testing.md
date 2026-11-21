# Java Data Access Setup and Testing

이 과정의 예시는 Java 17, Jakarta Persistence 3.1, Hibernate ORM 6.6, PostgreSQL 17을 기준으로 한다. 설정은 Hibernate와 JDBC를 직접 사용하는 형태로 설명한다. [Hibernate ORM 6.6 시작하기](https://docs.hibernate.org/orm/6.6/introduction/html_single/) · [Jakarta Persistence 3.1 명세](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 1. 데이터 접근 스택

| 계층 | 확인할 동작 |
| --- | --- |
| 애플리케이션 | 트랜잭션 경계, 조회 범위, 반환할 데이터 |
| JPA와 Hibernate | 엔티티 상태, JPQL/HQL의 SQL 변환, 플러시와 페치 전략 |
| JDBC와 커넥션 풀 | 파라미터 바인딩, 배치 실행, 연결 대여와 반환 |
| PostgreSQL | 접근 경로와 실행 계획, 잠금, 디스크 및 버퍼 접근 |

주문 목록을 읽는 호출이 느리다면 애플리케이션 요청에서 생성한 SQL 수와 반환 행 수를 먼저 확인한다. SQL 한 건의 비용이 크면 실제 바인딩 조건과 유사한 값으로 실행 계획을 확인한다. DB 실행은 짧고 연결 대기가 길다면 풀 지표에서 대여 지연과 점유 시간을 확인한다. [Hibernate 아키텍처](https://docs.hibernate.org/orm/6.6/userguide/html_single/#architecture) · [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)

## 2. 강의 예제 저장소 사용하기

저자가 공개한 저장소에는 책과 강의의 JDBC, JPA, Hibernate 예제가 있다. 같은 주제라도 모듈마다 Hibernate 버전과 DB 방언이 다를 수 있으므로 선택한 모듈의 빌드 파일과 테스트 데이터소스를 먼저 확인한다. 실습에서는 테스트 클래스 한 개를 실행해 초기화, 트랜잭션 경계, SQL, 결과 단언의 순서로 읽는다. 재현 결과에는 소스 리비전과 의존성 버전, DB 버전을 함께 기록한다. [강의 공식 예제 저장소](https://github.com/vladmihalcea/high-performance-java-persistence)

## 3. 실행 SQL과 바인딩 값 기록하기

Hibernate 6에서 SQL은 로거 `org.hibernate.SQL`의 DEBUG, 바인딩은 `org.hibernate.orm.jdbc.bind`의 TRACE에서 볼 수 있다. 로그 설정 문법은 사용하는 백엔드에 따른다. `hibernate.format_sql=true`는 SQL을 읽기 쉽게 들여쓰고, `hibernate.show_sql=true`는 SQL을 표준 출력에 보낸다. 바인딩 로그는 개인정보를 포함할 수 있으므로 합성 데이터를 쓰는 실습에서 켠다. [Hibernate SQL 로깅](https://docs.hibernate.org/orm/6.6/introduction/html_single/#logging-sql)

```text
org.hibernate.SQL = DEBUG
org.hibernate.orm.jdbc.bind = TRACE
```

SQL 로그로 문장의 순서와 형태를 확인한다. 드라이버에서 실행된 배치 수나 서버에 도착한 명령 수는 JDBC 계측과 DB 지표로 따로 측정한다. [Hibernate 통계 API](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/stat/Statistics.html)

## 4. 스키마 생성과 버전 관리

실습 DB는 Hibernate의 `hibernate.hbm2ddl.auto=create-drop`으로 초기화할 수 있다. 공유 환경에서는 Flyway 같은 마이그레이션 도구로 변경을 순서대로 적용하고 `hibernate.hbm2ddl.auto=validate`로 시작 시 매핑 호환성을 검사한다. 신규 설치와 기존 스키마에서의 업그레이드를 각각 검증하고, 인덱스나 업무 제약은 DB 카탈로그 및 통합 테스트에서 확인한다. 이미 적용한 버전의 변경이 필요하면 새 버전 파일을 추가한다. [Hibernate 스키마 관리](https://docs.hibernate.org/orm/6.6/userguide/html_single/#schema-generation) · [Flyway 버전 마이그레이션](https://documentation.red-gate.com/fd/versioned-migrations-273973333.html)

## 5. Docker로 데이터 접근 통합 테스트하기

Testcontainers의 PostgreSQL 모듈로 테스트 DB를 띄우고 애플리케이션과 같은 마이그레이션을 적용한다. 예제는 Testcontainers 1.x의 PostgreSQL 모듈을 사용한다. `jdbc:tc:` URL로 연결하려면 PostgreSQL JDBC 드라이버와 실행 가능한 Docker 환경이 필요하다. [Testcontainers JDBC 연결](https://java.testcontainers.org/modules/databases/jdbc/) · [PostgreSQL 모듈](https://java.testcontainers.org/modules/databases/postgres/)

```properties
jakarta.persistence.jdbc.url=jdbc:tc:postgresql:17:///persistence_lab
jakarta.persistence.jdbc.driver=org.testcontainers.jdbc.ContainerDatabaseDriver
```

저장 테스트에서는 `flush()` 뒤 `clear()`하고 다시 읽어 SQL 결과를 확인한다. 커밋 시점 제약이나 잠금 충돌은 독립된 트랜잭션으로 검증한다. 조회 비용을 비교할 때는 데이터 준비를 끝낸 뒤 측정을 시작하고, 필요한 연관관계까지 접근한 구간의 SQL 수를 기록한다.
