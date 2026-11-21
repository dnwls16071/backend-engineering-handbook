# JDBC Connections, Pooling, and Hibernate Statistics

연결 풀에서 대여하는 JDBC 연결과 DB 서버 세션은 수명이 다르다. 연결을 오래 점유하는 구간부터 측정하면 풀 대기와 SQL 지연을 구분할 수 있다. [Hibernate JDBC 연결](https://docs.hibernate.org/orm/6.6/userguide/html_single/#database-access) · [HikariCP 설정](https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby)

## 1. 데이터소스와 Hibernate ConnectionProvider

`DataSource`는 JDBC 연결을 공급한다. 풀을 사용하면 애플리케이션은 논리 연결을 대여하고 `Connection.close()`로 반환한다. 풀은 물리 연결을 재사용한다. Hibernate의 `ConnectionProvider`는 Hibernate가 연결을 얻고 반환하는 SPI다. 명시한 `hibernate.connection.provider_class`가 우선하며, `hibernate.connection.datasource`로 풀링하는 데이터소스를 전달할 수 있다. 연결 URL만 제공했을 때 선택될 수 있는 Hibernate 내장 풀은 실습용이다. [Hibernate ConnectionProvider](https://docs.hibernate.org/orm/6.6/userguide/html_single/#database-access-connectionprovider)

## 2. 트랜잭션과 연결 수명 주기

Hibernate 6.6에서 `RESOURCE_LOCAL`의 기본 처리 모드는 `DELAYED_ACQUISITION_AND_RELEASE_AFTER_TRANSACTION`이다. 트랜잭션 시작 시 자동 커밋을 끄기 위해 실제 연결을 즉시 빌릴 수 있다. 풀에서 대여한 **모든** 연결의 자동 커밋이 이미 꺼져 있다면 다음과 같이 구성해 SQL이 필요한 시점까지 대여를 미룰 수 있다. JTA의 기본값은 문장 실행 후 반환하는 모드이며 실제 반환 가능 여부는 연결 공급자와 컨테이너의 동작에 따른다. [Hibernate 연결 처리 모드](https://docs.hibernate.org/orm/6.6/userguide/html_single/#database-access-connection-handling)

```properties
# HikariConfig에 적용하는 설정
autoCommit=false

# Hibernate에 전달하는 설정
hibernate.connection.provider_disables_autocommit=true
```

이 두 속성은 각각 다른 설정 객체에 전달한다. `provider_disables_autocommit`은 공급자에 대한 약속이다. 자동 커밋이 켜진 연결이 섞이면 트랜잭션 경계가 깨질 수 있다. [Hibernate 설정 API](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/cfg/JdbcSettings.html)

## 3. 풀과 DB 세션 모니터링

| 관찰 대상 | 확인 항목 |
| --- | --- |
| 풀 | 활성·유휴 연결, 대기 스레드, 대여 지연, 획득 타임아웃 |
| 애플리케이션 | 트랜잭션 소요 시간, 한 요청이 점유하는 연결 수, 트랜잭션 내부의 외부 호출 |
| DB | 활성 쿼리, 잠금 대기, `idle in transaction` 세션과 트랜잭션 시작 시각 |

풀 대기가 늘었을 때 활성 연결의 쿼리가 잠금에 막혔는지, 연결을 가진 채 다른 I/O를 기다리는지 확인한다. HikariCP의 `connectionTimeout`은 풀에서 연결을 얻는 대기 한도다. 연결을 얻은 후의 문장 실행 시간 한도는 JDBC나 DB에서 별도로 설정한다. [HikariCP 설정](https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby) · [PostgreSQL pg_stat_activity](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)

## 4. Hibernate Statistics 읽기

`hibernate.generate_statistics=true`로 팩토리 수준 통계를 수집할 수 있다. 격리된 테스트에서는 준비 완료 후 초기화하고 측정 대상 트랜잭션을 실행해 카운터를 확인한다. 공유 팩토리에서는 여러 세션의 작업이 합산되므로 한 요청의 값처럼 해석하면 실제 비용을 잘못 판단할 수 있다. [Hibernate Statistics](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/stat/Statistics.html)

| 메서드 | 의미 |
| --- | --- |
| `getConnectCount()` | Hibernate 세션이 JDBC 연결을 얻은 횟수 |
| `getPrepareStatementCount()` | Hibernate가 JDBC prepared statement를 확보한 횟수 |
| `getFlushCount()` | 플러시 횟수 |
| `getSecondLevelCacheHitCount()` | 2차 캐시 적중 횟수 |

물리 연결 개수는 풀에서 보고, 서버에 수행된 SQL과 쿼리별 비용은 DB 쪽에서 확인한다.
