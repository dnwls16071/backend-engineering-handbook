# The First Five Minutes of Aurora MySQL Incident Triage

사용자 지연과 오류를 같은 시각의 DB 지표에 대응시킨다. 서비스 영향이 확인되면 즉시 완화하고, 원인 후보는 다음 관측으로 검증한다.

## 1. 서비스 지연·오류와 DB 지표 연결하기

UTC 기준으로 느려진 API와 오류 시작을 표시한다. 503이 로드 밸런서, 애플리케이션, 풀 획득 단계 중 어디서 발생했는지 찾는다. 같은 길이의 창과 같은 인스턴스 차원에서 Writer·Reader의 부하 및 연결, API 요청 수, 풀 대기를 비교한다. 지표가 동시에 변해도 원인을 확인하려면 대기 종류와 실행 경로를 대조해야 한다. [Aurora CloudWatch 지표](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)

## 2. CPU 사용률과 DB Load 따로 읽기

`CPUUtilization`은 인스턴스 CPU의 사용 비율이다. DB Load의 단위는 평균 활성 세션 수(AAS)이며, CPU에서 실행 중인 세션과 엔진에서 대기하는 세션을 포함한다. CPU가 낮아도 락이나 커밋 확인 대기가 늘면 DB Load는 높을 수 있다. vCPU 수와 DB Load를 대조할 때는 CPU 부분과 대기별 부분을 나눠 읽는다. [Aurora DB Load와 AAS](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_PerfInsights.Overview.ActiveSessions.html)

## 3. Top SQL과 대기 이벤트로 범위 좁히기

Database Insights에서 해당 인스턴스와 장애 구간의 DB Load를 대기 및 SQL로 분할한다. 행 락이 크면 [차단 세션](09_locks_deadlocks_connection_pools_and_retries.md)을 보고, CPU 비중이 크면 호출 수와 실행당 비용을 분리한다. 연결에 권한이 있다면 아래 쿼리로 현재 표시되는 비유휴 연결을 확인한다. 한 시점의 스냅샷은 장애 구간의 AAS와 별개다. [Aurora MySQL 대기 이벤트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Reference.Waitevents.html) · [MySQL Performance Schema threads](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-threads-table.html)

```sql
SELECT PROCESSLIST_ID, PROCESSLIST_DB, PROCESSLIST_COMMAND,
       PROCESSLIST_TIME, PROCESSLIST_STATE
FROM performance_schema.threads
WHERE TYPE = 'FOREGROUND' AND PROCESSLIST_ID IS NOT NULL
  AND PROCESSLIST_ID <> CONNECTION_ID()
  AND PROCESSLIST_COMMAND <> 'Sleep'
ORDER BY PROCESSLIST_TIME DESC
LIMIT 20;
```

## 4. 트래픽, 배포, 배치에서 원인 후보 찾기

시간축에 부하 시작, 배포 완료, 배치 시작, 캐시 만료를 놓는다. 동일 SQL이 더 자주 호출됐는지, 새 SQL이 나갔는지, 실제 연결 대상이 바뀌었는지 비교한다. 조회만 바뀐 릴리스가 Writer의 풀을 쓰게 됐다면 롤백 전후에 해당 호출량과 Writer 부하가 함께 달라지는지 확인한다.

## 5. 즉시 완화와 원인 해결을 나누기

사용자 실패가 지속되면 영향이 확인된 요청이나 배치만 제한하고 효과를 관찰한다. 운영 조치마다 시작 시각, 기대하는 지표 변화, 원복 조건을 남긴다. 이후 재현 환경에서 인덱스, 쿼리나 트랜잭션 경계를 개선한다. 연결과 재시도, 중복 주문 결과까지 확인한 뒤 사고를 종료한다.
