# Database Connections and Pooling

## 1. DB 커넥션이란 무엇이고, 생성 비용이 큰 이유는 무엇인가요?

**30–60초 답변**

> DB 커넥션은 클라이언트가 DB 서버에 SQL을 보내고 트랜잭션과 세션 상태를 유지하는 통신 경로입니다. 일반적인 원격 연결에서는 TCP 연결을 설정하고, TLS를 쓴다면 핸드셰이크를 거친 뒤 DB 프로토콜에서 사용자 인증과 세션 설정을 합니다. 예를 들어 PostgreSQL은 클라이언트 연결을 담당할 서버 프로세스를 사용합니다. 새 연결에는 네트워크 왕복과 인증 작업이 들고, 유지하는 커넥션에도 서버 자원이 필요합니다. 짧은 쿼리마다 새 연결을 만들면 설정 시간의 비중이 커질 수 있습니다. [PostgreSQL 서버 아키텍처](https://www.postgresql.org/docs/18/tutorial-arch.html) · [PostgreSQL 연결 시작과 TLS 흐름](https://www.postgresql.org/docs/18/protocol-flow.html)

**꼬리 질문 · 배포 직후 첫 DB 요청만 느리다면 무엇을 확인하나요?**

커넥션을 빌리는 시간과 빌린 뒤 쿼리를 보내서 결과를 받는 시간을 분리합니다. 획득만 느리다면 초기 풀에 사용 가능한 연결이 있었는지, 연결 생성이 DNS·TCP·TLS·DB 인증 중 어디에서 지연됐는지 확인합니다. 획득은 빠르지만 첫 실행만 느리면 쿼리 계획과 캐시 상태도 살펴봅니다. [HikariCP 커넥션 풀 설정](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) · [PostgreSQL 프로토콜 흐름](https://www.postgresql.org/docs/18/protocol-flow.html)

## 2. 커넥션 풀은 무엇이며 왜 사용하나요?

**30–60초 답변**

> 커넥션 풀은 실제 DB 커넥션을 유지하면서 요청에 빌려주고 회수합니다. Java의 풀에서 `getConnection()`으로 빌린 커넥션에 `close()`를 호출하면, 일반적으로 실제 연결을 매번 끊는 대신 풀로 반환합니다. 재사용으로 연결 설정 비용을 줄이고, 최대 크기를 정해 여러 요청이 한꺼번에 DB에 접속하는 규모도 제한합니다. 풀에 빈 커넥션이 없으면 요청은 짧게 대기하고, 대기 한도를 넘으면 실패합니다. 호출 코드가 커넥션을 제때 반환하도록 예외를 포함한 종료 경로를 관리합니다. [HikariCP 커넥션 획득과 최대 크기](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) · [HikariCP의 JDBC 프록시 반환 구현](https://github.com/brettwooldridge/HikariCP/blob/dev/src/main/java/com/zaxxer/hikari/pool/ProxyConnection.java)

**꼬리 질문 · 커넥션을 반환하면 DB 세션이 처음 상태로 완전히 돌아가나요?**

풀은 일반적으로 미완료 트랜잭션과 JDBC를 통해 바꾼 연결 속성을 관리하지만, SQL로 바꾼 세션 변수나 임시 테이블까지 모두 자동 정리하는지는 구현과 설정에 따라 다릅니다. 세션 상태를 바꾸는 코드가 있다면 그 범위를 제한하고, 반환 전에 원상 복구하거나 풀의 초기화 정책을 확인합니다. [HikariCP JDBC 연결 상태 정리](https://github.com/brettwooldridge/HikariCP/blob/dev/src/main/java/com/zaxxer/hikari/pool/ProxyConnection.java) · [PostgreSQL 세션 상태 정리 명령](https://www.postgresql.org/docs/18/sql-discard.html)

## 3. 커넥션 풀 크기는 클수록 좋은가요?

**30–60초 답변**

> 풀을 늘리면 앱에서 커넥션을 기다리던 요청을 더 많이 DB로 보낼 수 있습니다. 하지만 DB가 이미 CPU, I/O 또는 락 경합으로 포화됐다면 DB 내부 대기와 요청 지연이 늘 수 있습니다. 안정된 부하에서 초당 400번 커넥션을 빌리고 한 번에 평균 50ms 보유한다면, Little의 법칙에 따라 평균 약 20개가 동시에 사용됩니다. 이 수치를 출발점으로 삼고 실제 트래픽 변동, 대기 시간과 처리량을 보며 상한을 조정합니다. 인스턴스별 풀 크기에 배포 중 동시에 실행될 인스턴스 수를 곱하고, 배치나 운영 연결에 필요한 여유도 DB 용량에 포함합니다. [Little의 대기열 공식](https://pubsonline.informs.org/doi/epdf/10.1287/opre.9.3.383) · [HikariCP 풀 크기와 포화](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) · [PostgreSQL 연결 수와 예약 슬롯](https://www.postgresql.org/docs/18/runtime-config-connection.html)

**꼬리 질문 · 풀 대기열이 길어졌다면 바로 크기를 늘리나요?**

풀의 활성 커넥션, 획득 대기·보유 시간과 DB의 처리량, CPU, 락 대기를 같은 구간에서 확인합니다. 보유 시간이 늘어난다면 느린 쿼리나 트랜잭션을 오래 잡는 코드부터 좁힙니다. DB에 처리 여유가 있을 때는 부하 테스트에서 풀 상한을 조금씩 바꿔 성공 처리량과 p95·p99가 함께 개선되는지 확인합니다. [HikariCP 풀 크기 안내](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) · [PostgreSQL `pg_stat_activity`](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)

## 4. 커넥션 타임아웃과 리드 타임아웃은 어떻게 다르고 왜 필요한가요?

**30–60초 답변**

> 어떤 단계의 설정인지 먼저 확인합니다. MySQL Connector/J의 `connectTimeout`은 새 소켓 연결을 맺는 데 허용할 시간이고, 리드 타임아웃은 연결된 소켓에서 데이터를 기다리는 시간의 한도입니다. 예를 들어 PostgreSQL JDBC 드라이버는 이 읽기 대기 한도를 `socketTimeout`으로 설정합니다. HikariCP의 `connectionTimeout`은 앱이 풀에서 사용 가능한 커넥션을 얻기까지의 대기 한도입니다. DB 서버의 `statement_timeout`처럼 쿼리 실행을 서버에서 제한하는 설정도 별도로 둘 수 있습니다. 각 대기 시간을 제한하면 느린 DB 호출이 요청 스레드나 커넥션을 계속 점유하는 상황을 줄일 수 있습니다. [MySQL Connector/J 네트워킹 속성](https://dev.mysql.com/doc/connector-j/en/connector-j-connp-props-networking.html) · [pgJDBC 연결과 읽기 타임아웃](https://jdbc.postgresql.org/documentation/use/) · [HikariCP의 커넥션 대기 설정](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) · [PostgreSQL 문장 타임아웃](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-STATEMENT-TIMEOUT)

**꼬리 질문 · 커밋 응답을 기다리다 타임아웃이 나면 같은 쓰기를 곧바로 재시도하나요?**

응답을 받지 못했어도 서버에서 커밋이 끝났을 수 있습니다. 주문 번호나 작업 식별자로 처리 결과를 조회하거나, DB 유일성 제약과 멱등성 키로 중복을 막도록 설계한 요청만 같은 키로 다시 보냅니다. 풀 획득 단계에서 발생한 오류와 SQL 전송 이후의 오류를 로그에서 구분하면 재시도 판단이 쉬워집니다. [PostgreSQL 쿼리·취소 프로토콜](https://www.postgresql.org/docs/18/protocol-flow.html) · [AWS의 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 5. 커넥션 풀 상태는 어떻게 모니터링하고 문제를 진단하나요?

**30–60초 답변**

> 활성·유휴 커넥션, 최대 크기, 대기 중인 요청 수와 함께 획득 시간, 보유 시간, 획득 타임아웃을 봅니다. 예를 들어 HikariCP와 Micrometer에서는 `hikaricp.connections.active`, `.idle`, `.pending`, `.max`, 그리고 커넥션 획득·사용 시간을 확인할 수 있습니다. 활성 수가 상한에 닿고 대기 시간이 늘면 풀에 여유가 부족하다는 신호입니다. 왜 반환이 늦는지는 DB의 장기 쿼리, 락 대기, 유휴 트랜잭션과 대조합니다. 활성 수가 상한 아래인데 획득이 실패한다면 새 연결 생성 오류, DB 연결 제한과 네트워크 상태도 검사합니다. [HikariCP Micrometer 지표 정의](https://github.com/brettwooldridge/HikariCP/blob/dev/src/main/java/com/zaxxer/hikari/metrics/micrometer/MicrometerMetricsTracker.java) · [PostgreSQL `pg_stat_activity`와 대기 이벤트](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)

**꼬리 질문 · 오래 빌린 커넥션과 누수를 어떻게 구분하나요?**

PostgreSQL의 `pg_stat_activity`에서 쿼리 시작, 트랜잭션 시작과 대기 종류를 보고, 앱의 요청이 끝난 뒤에도 연결이 풀로 돌아오지 않는지 추적합니다. HikariCP의 `leakDetectionThreshold` 로그는 대여가 지정 시간보다 길었다는 신호로, 장기 트랜잭션도 걸릴 수 있습니다. 같은 호출 지점에서 반환이 반복해서 빠지는지와 정상 부하가 돌아온 뒤에도 활성 수가 내려가지 않는지를 확인합니다. [HikariCP 대여 추적 설정](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) · [PostgreSQL 활동 통계](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)
