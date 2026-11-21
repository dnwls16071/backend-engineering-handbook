# Database Performance, Reliability, and Operations

## 42. 느린 쿼리가 발생하면 어떻게 원인을 찾고 개선하나요?

**30–60초 답변**

> 먼저 지연이 시작된 시점과 영향받은 API를 확인하고, 애플리케이션의 커넥션 풀 대기와 DB 실행 시간을 나눠 봅니다. MySQL의 Performance Schema나 PostgreSQL의 `pg_stat_statements`에서 호출 횟수와 누적 실행 시간이 늘어난 SQL을 찾고, 실행 중인 세션에서 잠금이나 I/O 대기가 있는지 확인합니다. 잠금 대기라면 막고 있는 트랜잭션부터 찾습니다. 실행 자체가 느리다면 당시 파라미터로 실행 계획을 확인하고, 예상 행 수 오차가 큰 지점은 통계와 데이터 분포를, 실제 작업량이 큰 지점은 스캔 범위와 조인 조건을 점검합니다. 원인에 맞춰 SQL이나 인덱스를 바꾸고, 같은 조건의 실행 시간과 서비스 p95를 비교해 효과를 확인합니다. [MySQL 문장 통계](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) · [PostgreSQL 문장 통계](https://www.postgresql.org/docs/18/pgstatstatements.html)

**꼬리 질문 · 새 배포 직후 지연이 급증했다면요?**

배포 시각과 지연 시작 시각을 맞춰 보고, 이전 버전과 새 버전이 실행하는 SQL과 호출 빈도를 비교합니다. 변경과 지연의 연관성이 확인되고 바로 되돌릴 수 있으면 기능 플래그를 끄거나 호환성을 확인한 뒤 배포를 롤백합니다. 배치가 부하를 유발했다면 일시 중지하고, 잠금이라면 MySQL의 `data_lock_waits`나 PostgreSQL의 `pg_blocking_pids()`로 차단 세션을 찾습니다. 트랜잭션을 종료할 때는 어떤 작업이 롤백되는지 확인하고, 조치 뒤 요청 지연과 오류율이 정상 범위로 돌아오는지 봅니다. [MySQL 잠금 대기 테이블](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-lock-tables.html) · [PostgreSQL 차단 세션 조회](https://www.postgresql.org/docs/18/functions-info.html)

## 43. `EXPLAIN`과 `EXPLAIN ANALYZE`는 어떻게 읽나요?

**30–60초 답변**

> `EXPLAIN`은 옵티마이저가 고른 스캔·조인 방식과 예상 행 수를 보여 줍니다. 비용은 옵티마이저의 비교 단위입니다. `EXPLAIN ANALYZE`는 SQL을 실제 실행해 각 연산의 시간과 반환 행 수, 반복 횟수를 보여 줍니다. 예상 행 수가 크게 빗나간 지점을 찾고 조인 선택에 어떤 영향을 줬는지 봅니다. 중첩 루프의 안쪽에서 회당 3행을 반환하는 조회가 500회 반복됐다면 약 1,500행을 반환한 셈입니다. MySQL 8.4에서는 `TREE` 형식의 계획과 Performance Schema의 파일 I/O 통계를 함께 봅니다. PostgreSQL에서는 `EXPLAIN (ANALYZE, BUFFERS)`로 버퍼 적중·읽기와 임시 블록 사용도 확인합니다. [MySQL 실행 계획 실측](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze) · [MySQL 파일 I/O 통계](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-file-summary-tables.html) · [PostgreSQL 실행 계획 읽기](https://www.postgresql.org/docs/18/using-explain.html)

**꼬리 질문 · 운영 DB에서 `EXPLAIN ANALYZE`를 바로 실행해도 되나요?**

일반 `EXPLAIN`으로 범위를 먼저 보고, 실측은 대표 데이터와 파라미터를 갖춘 검증 환경에서 합니다. 대량 조회도 CPU와 I/O를 쓰고, DB가 지원하는 변경문을 붙이면 실제 변경이 일어납니다. 롤백을 해도 실행 중 발생한 잠금과 부하는 이미 서비스에 영향을 줄 수 있습니다. 또 PostgreSQL 계획의 `shared read`에는 OS 페이지 캐시에서 읽은 경우도 포함될 수 있어 실제 저장장치 병목은 OS의 I/O 지연과 대기 지표를 함께 봅니다. [MySQL `EXPLAIN ANALYZE`](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze) · [PostgreSQL `EXPLAIN` 옵션](https://www.postgresql.org/docs/18/sql-explain.html) · [PostgreSQL I/O 통계 해석](https://www.postgresql.org/docs/18/monitoring-stats.html)

## 44. 데이터가 계속 늘어나면 어떻게 확장하나요?

**30–60초 답변**

> 먼저 조회 지연, 쓰기 처리량, 저장 공간 중 어느 쪽이 한계인지 확인합니다. 자주 쓰는 쿼리가 필요 이상의 데이터를 읽는다면 SQL과 인덱스부터 조정하고, 오래된 데이터는 보관 정책에 맞춰 삭제하거나 아카이빙합니다. 기간 조회와 만료 데이터 정리가 주된 작업이라면 날짜 파티션으로 읽는 범위와 삭제 비용을 줄일 수 있습니다. 읽기 부하가 크고 최신성 지연을 허용하는 요청은 읽기 복제본으로 보냅니다. 단일 노드의 쓰기나 저장 용량이 여전히 한계라면 샤드 키를 기준으로 데이터를 나눕니다. 이때 자주 함께 읽고 쓰는 데이터를 같은 샤드에 두고, 부하 편중과 재분배 비용을 확인합니다. [PostgreSQL 테이블 파티셔닝](https://www.postgresql.org/docs/18/ddl-partitioning.html) · [MySQL 복제 활용](https://dev.mysql.com/doc/refman/8.4/en/replication.html) · [Vitess 샤딩](https://vitess.io/docs/reference/features/sharding/)

**꼬리 질문 · 주문 테이블을 월별로 나누면 모든 조회가 빨라지나요?**

조회 조건에서 월별 파티션 키의 범위를 알아낼 수 있어야 불필요한 파티션을 건너뛸 수 있습니다. 최근 한 달 조회에는 유리하지만, 주문 ID만으로 조회하면 여러 파티션을 확인할 수 있습니다. 실제 SQL의 실행 계획에서 접근 파티션을 확인하고, 월별 정리 비용이 줄어드는 효과와 자주 쓰는 ID 조회 비용을 함께 비교합니다. [PostgreSQL 파티션 프루닝](https://www.postgresql.org/docs/18/ddl-partitioning.html#DDL-PARTITION-PRUNING)

## 45. 클러스터링, 복제, 샤딩은 어떻게 다른가요?

**30–60초 답변**

> 운영 아키텍처에서 클러스터링은 여러 DB 노드를 하나의 서비스로 묶어 운영하는 구성입니다. 제품에 따라 노드 장애 시 역할 전환이나 요청 라우팅까지 맡습니다. 복제는 같은 데이터의 사본을 다른 노드에 유지하는 방식으로, 장애 조치나 읽기 분산에 활용합니다. 샤딩은 테넌트 ID 같은 키로 서로 다른 행을 여러 서버에 나눠 쓰기와 저장 용량을 분산하는 방식입니다. 세 가지는 함께 쓸 수 있습니다. 테넌트별 샤드를 두고, 각 샤드 내부를 복제 기반 클러스터로 운영하는 구성이 그 예입니다. [MySQL InnoDB Cluster](https://dev.mysql.com/doc/refman/8.4/en/mysql-innodb-cluster-introduction.html) · [MySQL 복제](https://dev.mysql.com/doc/refman/8.4/en/replication.html) · [Vitess 샤딩](https://vitess.io/docs/reference/features/sharding/)

**꼬리 질문 · 클러스터드 인덱스에서 말하는 클러스터링도 같은 뜻인가요?**

그 문맥에서는 한 테이블 안에서 행을 어떻게 저장하느냐를 말합니다. InnoDB는 보통 기본 키를 클러스터드 인덱스로 사용하고, 그 리프에 행 데이터를 저장합니다. 여러 노드를 운영하는 클러스터를 설명할 때는 장애 조치나 요청 라우팅 같은 노드의 역할을 설명합니다. [MySQL InnoDB의 클러스터드 인덱스와 보조 인덱스](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)

## 46. 복제는 어떻게 동작하며 동기 복제와 비동기 복제는 어떻게 다른가요?

**30–60초 답변**

> MySQL은 소스의 binlog 이벤트를 복제본의 릴레이 로그로 받아 적용하고, PostgreSQL 물리 복제는 주 서버의 WAL을 대기 서버가 받아 재생합니다. 비동기 복제는 복제본의 확인 응답을 기다리지 않고 커밋 성공을 반환하므로, 주 서버 장애 시 아직 전달하지 못한 변경을 잃을 수 있습니다. 동기 계열은 커밋 응답 전에 복제본의 특정 단계를 기다립니다. MySQL 세미싱크는 복제본의 릴레이 로그 디스크 기록을 기다립니다. PostgreSQL은 동기 대기 서버를 지정했을 때 `on`은 WAL이 영구 저장될 때까지, `remote_apply`는 재생되어 조회에 보일 때까지 기다립니다. 필요한 보장 수준에 따라 장애 시 손실 위험과 커밋 지연을 비교합니다. [MySQL 세미싱크 복제](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html) · [PostgreSQL 물리 복제](https://www.postgresql.org/docs/18/warm-standby.html) · [PostgreSQL `synchronous_commit`](https://www.postgresql.org/docs/18/runtime-config-wal.html)

**꼬리 질문 · 쓰기 성공 직후 복제본에서 조회하면 방금 쓴 값이 보이나요?**

조회 대상 복제본이 그 변경을 적용했는지에 달려 있습니다. MySQL 세미싱크는 적용 전에도 확인 응답을 보내고, 확인이 시간 안에 오지 않으면 비동기로 전환될 수 있습니다. PostgreSQL `remote_apply`의 적용 보장은 확인한 동기 대기 서버를 기준으로 합니다. 쓰기 직후 최신 값이 필요한 요청은 주 서버로 보내거나, 조회 대상 복제본이 해당 GTID나 WAL 위치까지 적용했음을 확인한 뒤 보냅니다. [MySQL 세미싱크 확인과 타임아웃](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html) · [MySQL GTID 함수](https://dev.mysql.com/doc/refman/8.4/en/gtid-functions.html) · [PostgreSQL 동기 복제](https://www.postgresql.org/docs/18/warm-standby.html#SYNCHRONOUS-REPLICATION)

## 47. 데드락은 무엇이고 왜 발생하나요?

**30–60초 답변**

> 데드락은 트랜잭션들의 잠금 대기 관계가 원을 이루는 상황입니다. 예를 들어 송금 트랜잭션 A가 계좌 1을 잠근 뒤 계좌 2를 기다리고, 트랜잭션 B가 계좌 2를 잠근 뒤 계좌 1을 기다리면 둘 다 진행할 수 없습니다. 한쪽만 기다리는 일반적인 잠금 대기는 상대가 커밋하거나 롤백하면 풀립니다. 데드락을 줄이려면 어느 방향으로 송금하든 계좌 ID가 작은 쪽부터 잠그도록 모든 처리 경로에서 순서를 맞춥니다. 트랜잭션을 짧게 유지하고, 변경할 행을 효율적으로 찾도록 인덱스를 확인해 잠금이 겹칠 가능성도 줄입니다. [PostgreSQL 데드락](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS) · [MySQL 데드락 예방](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html)

**꼬리 질문 · 트랜잭션에서 SQL을 한 문장만 실행해도 데드락이 생기나요?**

생길 수 있습니다. 한 `UPDATE`가 여러 행을 잠그고, 동시에 다른 문장이 겹치는 행을 다른 순서로 잠그면 순환 대기가 만들어집니다. 실제 원인을 찾을 때는 SQL에 적힌 조건과 함께 실행 계획, 잠근 인덱스 레코드나 범위, 각 트랜잭션이 먼저 획득한 잠금을 봅니다. [MySQL InnoDB 데드락](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html) · [PostgreSQL 행 잠금과 데드락](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS)

## 48. 데이터베이스와 애플리케이션은 데드락을 어떻게 처리하나요?

**30–60초 답변**

> DB는 잠금 대기의 순환을 감지하면 트랜잭션 하나를 중단해 다른 쪽이 진행할 수 있게 합니다. InnoDB는 감지가 켜져 있으면 변경한 행이 적은 트랜잭션을 우선 롤백하고, PostgreSQL은 중단할 트랜잭션을 내부에서 고릅니다. 애플리케이션에서 MySQL 오류 `1213`이나 PostgreSQL SQLSTATE `40P01`을 확인하면 새 트랜잭션을 열고 업무 판단에 필요한 조회부터 다시 실행합니다. 재시도 횟수에는 상한을 두고 대기 간격을 조금씩 다르게 해 다시 충돌할 가능성을 낮춥니다. 반복되면 데드락 로그로 잠금 순서와 트랜잭션 범위를 조사합니다. [MySQL 데드락 감지](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html) · [MySQL 데드락 오류](https://dev.mysql.com/doc/mysql-errors/8.4/en/server-error-reference.html#error_er_lock_deadlock) · [PostgreSQL 데드락 처리](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS) · [PostgreSQL 오류 코드](https://www.postgresql.org/docs/18/errcodes-appendix.html)

**꼬리 질문 · 결제 API 호출까지 포함된 작업을 재시도하면 어떻게 되나요?**

DB 롤백으로 이미 승인된 외부 결제는 취소되지 않으므로 결제가 중복될 수 있습니다. 결제 API가 멱등성 키를 지원하면 같은 업무 요청을 재시도할 때 같은 키를 전달합니다. 커밋된 결과를 메시지로 알려야 한다면 업무 데이터와 전송할 이벤트를 한 트랜잭션에 기록합니다. 발행기는 커밋된 이벤트를 읽어 보내고, 수신 측은 이벤트 ID를 기준으로 중복 처리를 막습니다. [AWS 트랜잭셔널 아웃박스](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 49. 운영 중 데이터베이스 장애가 발생하면 어떤 순서로 대응하나요?

**30–60초 답변**

> 먼저 영향받은 기능과 시점을 확인하고 읽기·쓰기 오류, 지연, 연결 실패를 구분합니다. 앱에서만 접속할 수 없는지, 주 서버 자체가 실패했는지 다른 관측 경로로 확인합니다. 과부하라면 배치나 재시도를 줄여 부하를 낮춥니다. 주 서버 장애로 전환이 필요하면 기존 주 서버가 쓰기를 받을 수 없도록 격리합니다. 후보 복제본의 로그 수신·적용 위치로 누락 가능성을 파악하고, 허용 데이터 손실 범위에 들면 승격합니다. 연결 경로와 커넥션 풀을 새 주 서버로 전환하고, 실제 읽기·쓰기와 오류율, 복제 상태를 확인합니다. [PostgreSQL 장애 조치와 기존 주 서버 격리](https://www.postgresql.org/docs/18/warm-standby-failover.html) · [MySQL 복제 상태 확인](https://dev.mysql.com/doc/refman/8.4/en/replication-administration-status.html)

**꼬리 질문 · 주 서버에 접속할 수 없지만 실제로 살아 있는지 확신할 수 없다면요?**

네트워크가 분리되면 다른 경로의 클라이언트는 여전히 기존 주 서버에 쓸 수 있습니다. 기존 주 서버의 쓰기 권한을 차단하거나 노드를 격리하고, 그 조치가 보장될 때 승격합니다. 확인이 끝날 때까지 승격을 보류하면 두 서버가 다 쓰기를 받는 스플릿 브레인을 피할 수 있습니다. 복구한 기존 주 서버는 새 주 서버와 로그가 갈라졌는지 확인하고, 필요하면 데이터를 다시 맞춘 뒤 복제본으로 편입합니다. [PostgreSQL 장애 조치](https://www.postgresql.org/docs/18/warm-standby-failover.html) · [PostgreSQL `pg_rewind`](https://www.postgresql.org/docs/18/app-pgrewind.html)

## 50. 운영 중 데이터베이스의 어떤 지표를 모니터링하나요?

**30–60초 답변**

> 먼저 사용자 영향이 보이는 API의 p95·p99 응답 시간과 오류율, 요청량을 확인합니다. DB에서는 쿼리 호출 수와 누적 실행 시간, 풀에서 연결을 얻기까지의 대기 시간, 활성 세션과 잠금 대기를 같은 시간대에 봅니다. DB 실행 시간이 늘었다면 CPU와 디스크 지연, 임시 파일 사용을 비교해 스캔·정렬이 부담인지 확인합니다. 쓰기 응답이 늦다면 로그 쓰기와 동기화, 복제 확인 대기도 봅니다. 복제본 조회가 있다면 로그 수신과 적용 지연을 각각 확인합니다. 서비스 지표와 DB 지표를 함께 보면 사용자가 겪는 지연이 연결, 잠금, 실행 또는 복제 중 어디에서 생겼는지 좁힐 수 있습니다. [MySQL 문장 통계](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html) · [PostgreSQL 활동·I/O·복제 통계](https://www.postgresql.org/docs/18/monitoring-stats.html)

**꼬리 질문 · API가 느려졌는데 DB CPU가 낮으면 무엇을 보나요?**

커넥션 풀 대기와 DB 안에서의 실행 시간을 먼저 나눕니다. 풀 대기만 길다면 커넥션 점유 시간과 누수, 요청 동시성을 확인합니다. DB 실행 시간이 길다면 MySQL의 잠금·파일 I/O 통계나 PostgreSQL `pg_stat_activity`의 대기 이벤트에서 잠금, 디스크 I/O, 복제 응답 대기가 있는지 봅니다. 예를 들어 잠금 대기 세션이 늘었다면 CPU 증설 전에 차단하는 트랜잭션과 시작 시각을 확인합니다. [MySQL 잠금 대기](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-lock-tables.html) · [MySQL 파일 I/O](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-file-summary-tables.html) · [PostgreSQL 대기 이벤트](https://www.postgresql.org/docs/18/monitoring-stats.html#WAIT-EVENT-TABLE)
