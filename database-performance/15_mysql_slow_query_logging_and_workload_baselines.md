# MySQL Slow Query Logging and Workload Baselines

MySQL 8.4에서 슬로 쿼리 로그와 Performance Schema가 보여 주는 범위를 비교하고, 반복 실행되는 SQL을 총 실행 시간으로 정렬해 튜닝 대상을 고른다. 실습은 합성 주문 데이터와 로컬 컨테이너를 사용한다. [MySQL 슬로 쿼리 로그](https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html) · [MySQL 문장 집계](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)

## 1. 반복해서 측정할 기준 정하기

같은 시간대와 환경에서 DB의 누적 문장 시간, 호출 수, 읽은 행 수와 애플리케이션 지연을 비교한다. 예를 들어 주문 조회의 요청 p95가 높아졌다면 DB 실행 시간과 커넥션 풀 대기를 나눠 본다. 데이터 분포, 조회 조건, 처리량, 측정 구간을 함께 기록하면 튜닝 전후를 같은 기준으로 볼 수 있다. [데이터베이스 성능 측정과 병목 조사](01_database_performance_and_query_execution_architecture.md)

## 2. 로컬 실습 환경 시작하기

컨테이너 네트워크를 끄고 내부 소켓으로 접속한다. 루트 비밀번호를 비운 구성은 합성 데이터만 넣는 로컬 컨테이너에 사용한다. 기동 후 `docker logs mysql-query-lab`에서 초기화 이후 최종 서버가 연결을 받을 준비를 마쳤는지 확인한다. [Docker MySQL 공식 이미지](https://hub.docker.com/_/mysql)

```sh
docker run --detach --rm --network none --name mysql-query-lab \
  -e MYSQL_ALLOW_EMPTY_PASSWORD=yes \
  -e MYSQL_DATABASE=performance_lab \
  mysql:8.4 \
  --performance-schema=ON --slow-query-log=ON \
  --slow-query-log-file=/var/lib/mysql/slow-query-lab.log \
  --log-output=FILE --long-query-time=0.05

docker exec -it mysql-query-lab mysql -uroot performance_lab
```

MySQL 프롬프트에서 [공통 고객·주문 데이터 SQL](01_database_performance_and_query_execution_architecture.md#3-공통-실습-데이터)을 한 번 실행한다. 다음 문서에서도 이 데이터를 사용한다. 전체 실습을 마친 뒤 `docker stop mysql-query-lab`으로 컨테이너와 실습 데이터를 제거한다.

## 3. 슬로 쿼리 로그를 켜고 읽기

`slow_query_log`는 기록 여부, `log_output`은 출력 위치, `long_query_time`은 시간 기준을 정한다. `min_examined_row_limit`이 설정돼 있으면 최소 검사 행 수도 충족해야 한다. `long_query_time`의 전역 설정을 변경하면 기존 연결은 세션 값을 계속 쓰므로 연결별 적용 여부를 확인한다. [MySQL 슬로 쿼리 로그 설정](https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html)

```sql
SELECT @@GLOBAL.slow_query_log, @@GLOBAL.log_output,
       @@SESSION.long_query_time, @@SESSION.min_examined_row_limit;

SELECT SLEEP(0.08), order_id FROM perf5_orders WHERE order_id = 11;
SELECT SLEEP(0.08), order_id FROM perf5_orders WHERE order_id = 12;
```

다른 터미널에서 아래 명령을 실행한다. `Query_time`, `Lock_time`은 초 단위이며 `Rows_sent`와 `Rows_examined`는 각각 전송한 행과 검사한 행을 보여 준다. 초기 잠금을 얻기까지의 시간은 슬로 로그의 실행 시간 계산에 포함되지 않는다. 로그는 실행을 마치고 잠금을 해제한 뒤 기록된다. [MySQL 슬로 쿼리 로그의 기록 순서와 필드](https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html)

```sh
docker exec mysql-query-lab tail -n 24 /var/lib/mysql/slow-query-lab.log
```

## 4. Performance Schema와 sys에서 상위 지문 보기

`events_statements_summary_by_digest`의 집계 단위는 서버 안의 `(SCHEMA_NAME, DIGEST)`다. 아래 SQL은 누적 시간을 피코초에서 초로 바꿔 보여 준다. 사람이 빠르게 확인할 때는 `sys.statement_analysis`의 포맷된 값을 보고 집계 작업에서는 Performance Schema의 숫자 원본이나 `sys.x$statement_analysis`를 사용한다. [MySQL 문장 집계 테이블](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) · [Performance Schema 시간 단위](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-timing.html) · [sys.statement_analysis](https://dev.mysql.com/doc/refman/8.4/en/sys-statement-analysis.html)

```sql
SELECT DIGEST, DIGEST_TEXT, COUNT_STAR,
       ROUND(SUM_TIMER_WAIT / 1e12, 3) AS total_seconds,
       SUM_ROWS_EXAMINED
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = 'performance_lab' AND DIGEST IS NOT NULL
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;

SELECT query, exec_count, total_latency, rows_examined
FROM sys.statement_analysis
WHERE db = 'performance_lab'
LIMIT 10;
```

슬로 로그는 시간·행 수 조건을 충족한 개별 실행을 남긴다. 지문 집계로는 로그 임계값보다 빨리 끝나더라도 자주 호출되는 SQL의 누적 비용을 확인할 수 있다. 위 조회 결과는 현재 누적값이므로 하루 단위 비교에는 시점별 스냅샷의 차이를 사용한다. [지문 스냅샷과 자동 탐지](17_automating_mysql_slow_query_detection_with_a_cmdb.md)

## 5. 리터럴이 다른 SQL을 같은 지문으로 묶기

실습의 두 주문 조회는 `order_id` 값만 다르다. MySQL의 지문 정규화는 리터럴 값을 매개변수 마커로 바꾸고 공백과 주석을 정규화한다. 통계에서 같은 지문의 `COUNT_STAR`가 증가하는지 확인한다. 같은 지문 안에서도 특정 고객의 데이터가 몰려 있으면 실행 시간과 계획이 달라질 수 있다. 수집기가 별도 로그 파서로 지문을 만든다면 파서 버전을 함께 기록하고 집계 과정에서 MySQL의 `DIGEST`와 같은 값이라고 가정하지 않는다. [MySQL 문장 지문과 샘플링](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-digests.html)

## 6. 총 부하로 개선 순서 정하기

같은 한 시간 동안 평균 20ms인 조회가 10,000번 실행되면 누적 200초, 평균 2초인 조회가 10번 실행되면 누적 20초다. 전체 문장 시간 절감이 목표라면 첫 번째 조회가 우선 후보가 된다. 누적 실행 시간은 동시에 실행된 시간의 합일 수 있으므로 CPU 시간이나 시간당 서버 사용률로 읽지 않는다. 핵심 요청 SLA와 잠금 전파가 걸린 쿼리는 별도로 우선순위를 판단한다. 개선 후에는 동일 구간의 실행 수, 실행당 시간, 읽은 행 수를 함께 비교한다. [MySQL 문장 집계의 타이머와 실행 수](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)
