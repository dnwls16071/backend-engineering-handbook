# Inspecting MySQL Configuration, Access, and Performance

운영 중인 MySQL을 조사할 때는 서버와 세션에 적용된 설정, 접속 계정이 가진 권한, 실제 쿼리에서 관찰되는 비용을 확인한다. 실습 환경은 MySQL 8.4(InnoDB)다.

## 1. 글로벌 설정과 세션 설정

`SHOW GLOBAL VARIABLES`는 서버 설정을, `SHOW SESSION VARIABLES`는 현재 연결에 적용된 설정을 보여 준다. 글로벌·세션 범위를 모두 지원하는 변수의 글로벌 값을 바꾸면 새 연결이 그 값을 상속하지만, 이미 열려 있는 연결의 세션 값은 독립적이다. 동적 글로벌 변수의 `SET GLOBAL` 변경은 실행 중인 서버에 적용된다. `SET PERSIST`는 지원되는 설정을 실행 중인 서버에 적용하고 이후 재시작에도 쓰도록 저장한다. 변경 전에 변수의 범위와 동적 변경 지원 여부를 확인한다. [Using System Variables](https://dev.mysql.com/doc/refman/8.4/en/using-system-variables.html) · [Persisted System Variables](https://dev.mysql.com/doc/refman/8.4/en/persisted-system-variables.html)

```sql
SELECT @@GLOBAL.max_connections, @@GLOBAL.innodb_buffer_pool_size;
SELECT @@GLOBAL.transaction_isolation, @@SESSION.transaction_isolation;
SHOW GLOBAL VARIABLES LIKE 'slow_query_log';
```

## 2. 계정과 역할로 접근 범위 관리

MySQL 계정은 사용자 이름과 접속 호스트의 조합으로 식별한다. 애플리케이션의 읽기, 쓰기, 스키마 변경 권한을 실제 역할에 맞춰 부여한다. 역할은 권한 묶음이며 계정에 부여한 역할이 세션에서 활성화되어 있는지도 확인한다. `USER()`는 연결에 사용한 사용자 정보를, 일반 세션의 `CURRENT_USER()`는 권한 검사에 쓰인 계정을 보여 준다. [Account Names](https://dev.mysql.com/doc/refman/8.4/en/account-names.html) · [Using Roles](https://dev.mysql.com/doc/refman/8.4/en/roles.html)

```sql
SELECT USER(), CURRENT_USER(), CURRENT_ROLE();
SHOW GRANTS;
```

예를 들어 조회 전용 계정에는 필요한 테이블에 대한 `SELECT` 권한을 역할로 부여하고, 기본 역할을 지정한 다음 새 연결에서 활성화 여부를 확인한다. 애플리케이션에서 쓰는 계정과 마이그레이션을 실행하는 계정은 맡는 작업이 다르다.

## 3. 상태 지표에서 실행 계획까지

`Threads_running`은 `Sleep` 상태가 아닌 스레드 수를, `Threads_connected`는 현재 연결 수를 나타낸다. `Innodb_buffer_pool_reads`는 버퍼 풀에 페이지가 없어 디스크에서 읽어야 했던 횟수이며, `Innodb_buffer_pool_read_requests`는 전체 논리적 읽기 요청 수다. 누적 카운터는 같은 길이의 관측 구간마다 시작 값과 종료 값의 차이를 비교한다. [Server Status Variables](https://dev.mysql.com/doc/refman/8.4/en/server-status-variables.html)

```sql
SHOW GLOBAL STATUS
WHERE Variable_name IN (
    'Threads_connected', 'Threads_running',
    'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests'
);

SELECT SCHEMA_NAME, DIGEST_TEXT, COUNT_STAR, SUM_TIMER_WAIT / 1000000000000 AS total_seconds,
       SUM_ROWS_EXAMINED, SUM_ROWS_SENT
FROM performance_schema.events_statements_summary_by_digest
WHERE DIGEST IS NOT NULL
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```

문장 다이제스트에서 누적 실행 시간이 크거나 반환량에 비해 읽는 행이 많은 조회를 고른다. 실제 파라미터로 `EXPLAIN`의 접근 유형과 인덱스를 확인하고, 실측이 필요하면 조회를 실행하는 `EXPLAIN ANALYZE`를 통제된 실습 환경에서 사용한다. [Statement Summary Tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) · [Reading Execution Plans with EXPLAIN](../database-performance/02_reading_execution_plans_with_explain.md) · [Measuring Query Execution with EXPLAIN ANALYZE](../database-performance/03_measuring_query_execution_with_explain_analyze.md)
