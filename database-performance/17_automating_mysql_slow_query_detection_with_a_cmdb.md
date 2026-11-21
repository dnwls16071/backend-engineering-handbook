# Automating MySQL Slow Query Detection with a CMDB

MySQL 8.4의 지문 집계에서 일정 구간의 총 실행 시간을 계산하고, CMDB의 서비스·담당 팀 정보로 탐지 결과를 전달한다. 실습에서는 티켓 후보와 대시보드의 입력값까지만 조회한다. [MySQL 문장 집계 테이블](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)

## 1. 슬로 로그와 지문 집계를 매일 수집하기

슬로 로그는 개별 실행의 시각과 처리량을 분석하는 데 쓰고, 지문 스냅샷은 일정 구간의 실행 수와 누적 실행 시간을 비교하는 데 쓴다. 두 소스의 관측 범위가 겹치므로 실행 횟수를 서로 더하지 않는다. 슬로 로그 수집기는 파일 식별자와 읽은 위치를 저장한다. 파일이 회전하면 이전 파일의 남은 레코드를 처리하고 새 파일로 넘어간다. 저장에 성공한 뒤 읽은 위치를 갱신하고, 재시도에서 같은 레코드가 들어오면 파일 식별자와 레코드 시작 위치로 중복을 막는다. [MySQL 슬로 로그](https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html) · [MySQL 로그 유지 관리](https://dev.mysql.com/doc/refman/8.4/en/log-file-maintenance.html)

```sql
SELECT COALESCE(SCHEMA_NAME, '') AS schema_key,
       DIGEST, COUNT_STAR, SUM_TIMER_WAIT, SUM_ROWS_EXAMINED
FROM performance_schema.events_statements_summary_by_digest
WHERE DIGEST IS NOT NULL;
```

빈 문자열은 기본 스키마가 지정되지 않은 문장의 키로 예약한다. 지문이 NULL인 초과 집계 행은 개별 지문 순위에서 제외하고, 전체 실행 수에 대한 비율을 수집 상태로 확인한다. 이 행은 지문 집계 테이블이 가득 찬 뒤 기존 항목과 일치하지 않는 실행을 모은다. [MySQL 지문 집계의 크기와 초과 행](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-digests.html)

## 2. 구간 부하로 탐지 규칙 만들기

같은 서버의 같은 지문에 대해 시작과 끝 스냅샷의 차이를 계산한다. 실행 수 차이, `SUM_TIMER_WAIT` 차이, 검사 행 수 차이를 구한다. 평균 실행 시간은 구간 총 시간을 구간 실행 수로 나눈다. 실습 기준은 하루 동안 20회 이상 실행됐고 총 실행 시간이 5초 이상인 지문이다. 운영 임계값은 서비스 기준선과 업무 중요도에 맞춰 정한다. [MySQL 집계 컬럼과 시간 단위](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) · [Performance Schema Event Timing](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-timing.html)

이전 스냅샷이 없거나 카운터가 감소한 경우에는 비교 불가로 기록한다. 재시작, 집계 초기화, 인스턴스 교체도 수집 세대를 새로 만드는 조건이다. 카운터 감소만으로 모든 초기화를 잡을 수는 없으므로 서버 가동 정보와 운영 이벤트를 함께 사용한다. 긴 구간에 수집이 빠졌으면 일별 규칙에 그대로 넣지 않는다. 신규 지문이나 수집 실패 건수는 별도 지표로 남긴다.

## 3. 수집 결과의 저장 단위 정하기

스냅샷은 저장소의 대상 ID, 예약한 UTC 관측 시점, 스키마 키, digest로 식별한다. 같은 관측 작업을 재시도해도 키는 유지한다. 여러 레코드를 하나의 관측으로 적재할 때는 적재가 완전히 끝난 구간만 탐지에 사용한다. 재시도에서 이미 확정한 스냅샷을 덮어쓰면 구간 통계가 바뀌므로 저장 상태와 관측 시각을 기록한다.

시계열 집계 테이블에는 카운터와 수집 식별자만 저장한다. 장기 보존이 필요한 보고서는 구간 단위로 집계하고 상세 스냅샷의 보존 기간은 별도로 정한다.

## 4. 개인정보와 SQL 리터럴 마스킹

슬로 로그와 `QUERY_SAMPLE_TEXT`에는 이메일, 고객 ID, 자유 입력 데이터가 들어갈 수 있다. 아래 실습의 적재 스키마는 이 필드를 받지 않는다. 원문으로 분석이 필요한 로그는 접근을 제한한 저장소에 짧게 보관하고, 공유 데이터는 SQL 파서로 리터럴을 정규화한 뒤 민감한 식별자·주석·오류 문구까지 검사한다. 구문 분석에 실패한 이벤트는 공개 경로로 내보내지 않는다. `DIGEST_TEXT`에도 테이블·스키마 이름이 남을 수 있으므로 저장 대상은 필요에 따라 승인한 템플릿 또는 지문 해시로 제한한다. [MySQL 지문 정규화와 원문 샘플](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-digests.html)

## 5. CMDB에서 수집 대상과 소유권 관리하기

호스트 주소만으로는 서비스와 담당자를 확인하기 어렵다. CMDB에는 안정적인 대상 ID와 서비스, 환경, 연결 설정 참조, 담당 팀, 티켓 큐, 대시보드 식별자를 둔다. 접속 자격 증명은 인증 정보 저장소에서 참조로 조회한다. 운영 노드가 교체돼 같은 엔드포인트가 다른 DB를 가리키면 수집 세대를 분리한다.

## 6. CMDB와 스냅샷 테이블 만들기

실습은 관측 대상과 수집 저장소를 같은 MySQL 인스턴스의 서로 다른 스키마에서 재현할 수 있다. 수집 예제의 `SCHEMA_NAME`을 고정한 경우 다른 스키마의 쿼리가 집계에 섞이지 않는다. DDL과 아래 데이터는 빈 실습 스키마에 실행한다. `source_epoch`는 수집기가 인스턴스 교체나 집계 초기화를 확인할 때 새 값으로 지정하는 토큰이다.

```sql
CREATE TABLE cmdb_mysql_target (
    target_id BIGINT UNSIGNED PRIMARY KEY,
    service_name VARCHAR(80) NOT NULL,
    environment VARCHAR(20) NOT NULL,
    connection_ref VARCHAR(160) NOT NULL,
    owner_team VARCHAR(80) NOT NULL,
    ticket_queue VARCHAR(80) NOT NULL,
    dashboard_key VARCHAR(80) NOT NULL,
    collection_enabled BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE = InnoDB;

CREATE TABLE mysql_digest_snapshot (
    target_id BIGINT UNSIGNED NOT NULL,
    observed_at DATETIME(6) NOT NULL,
    schema_key VARBINARY(256) NOT NULL,
    digest CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    source_epoch BINARY(16) NOT NULL,
    exec_count BIGINT UNSIGNED NOT NULL,
    total_time_ps BIGINT UNSIGNED NOT NULL,
    rows_examined BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (target_id, observed_at, schema_key, digest),
    FOREIGN KEY (target_id) REFERENCES cmdb_mysql_target(target_id)
) ENGINE = InnoDB;
```

## 7. CMDB 한 행으로 수집·티켓·대시보드 연결하기

스케줄러는 `collection_enabled`인 행의 `connection_ref`로 대상을 선택한다. 탐지 결과는 `target_id`로 CMDB를 조회해 담당 팀과 티켓 큐, 대시보드에 연결한다. `target_id`와 스키마·지문, 관측 구간, 규칙 버전으로 작업 식별자를 만들어 같은 결과의 재전송이 중복 티켓을 만들지 않게 한다. 동일 문제가 다음 구간에도 이어지면 진행 중인 티켓에 구간 통계와 변화량을 추가할 수 있다. 티켓과 대시보드에는 원문 대신 지문과 집계값을 넘긴다.

## 8. 실습 · 두 스냅샷에서 부하 이상 찾기

첫 행 이후 실행 횟수는 30회, 총 실행 시간은 6초 증가한다. 두 수집 시점과 수집 세대가 같은 기준을 가리키는지 확인하고 나서 비교한다.

```sql
INSERT INTO cmdb_mysql_target
    (target_id, service_name, environment, connection_ref,
     owner_team, ticket_queue, dashboard_key, collection_enabled)
VALUES (1, 'orders', 'lab', 'mysql-query-lab',
        'orders-team', 'orders-performance', 'orders-mysql', TRUE);

INSERT INTO mysql_digest_snapshot
    (target_id, observed_at, schema_key, digest, source_epoch,
     exec_count, total_time_ps, rows_examined)
VALUES
    (1, '2025-01-15 00:00:00', 'performance_lab', REPEAT('a', 64),
     UNHEX(REPEAT('11', 16)), 100, 10000000000000, 15000),
    (1, '2025-01-16 00:00:00', 'performance_lab', REPEAT('a', 64),
     UNHEX(REPEAT('11', 16)), 130, 16000000000000, 21000);

WITH delta AS (
    SELECT e.target_id, e.schema_key, e.digest,
           CAST(e.exec_count AS DECIMAL(30, 0)) - s.exec_count AS executions,
           CAST(e.total_time_ps AS DECIMAL(30, 0)) - s.total_time_ps AS elapsed_ps,
           CAST(e.rows_examined AS DECIMAL(30, 0)) - s.rows_examined AS examined
    FROM mysql_digest_snapshot AS e
    JOIN mysql_digest_snapshot AS s
      ON s.target_id = e.target_id AND s.schema_key = e.schema_key
     AND s.digest = e.digest AND s.source_epoch = e.source_epoch
     AND s.observed_at = '2025-01-15 00:00:00'
    WHERE e.observed_at = '2025-01-16 00:00:00'
)
SELECT t.service_name, t.owner_team, t.ticket_queue, t.dashboard_key,
       d.schema_key, d.digest, d.executions,
       ROUND(d.elapsed_ps / 1000000000000, 3) AS total_seconds,
       ROUND(d.elapsed_ps / NULLIF(d.executions, 0) / 1000000000, 3) AS mean_ms,
       d.examined
FROM delta AS d
JOIN cmdb_mysql_target AS t ON t.target_id = d.target_id
WHERE t.collection_enabled AND d.executions >= 20
  AND d.elapsed_ps >= 5000000000000 AND d.examined >= 0
ORDER BY d.elapsed_ps DESC, d.target_id, d.schema_key, d.digest;
```

예상 결과는 티켓 후보 1건이다. `executions`는 30, `total_seconds`는 6.000, `mean_ms`는 200.000, `examined`는 6,000이다. 두 스냅샷의 `source_epoch`가 다르면 이 행은 구간 비교에서 제외된다.

## 9. 실습 · 대상의 수집 상태와 담당 큐 검증하기

`target_id = 1`의 `owner_team`과 `ticket_queue`를 바꾼 뒤 탐지 SELECT를 다시 실행한다. 카운터 차이는 같고 담당자와 큐는 새 설정을 따른다. 다음으로 `collection_enabled`를 끄고 후보가 사라지는지 확인한다. 수집기가 이 필터를 적용하는지도 별도로 점검한다. 이 테스트를 통해 수집, 라우팅, 대시보드가 같은 대상 키로 연결되는지 확인할 수 있다.
