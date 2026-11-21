# Managing MySQL Connections

MySQL 8.4에서는 서버의 연결 한도와 애플리케이션 풀의 크기를 함께 정한다. 인스턴스별 최대 풀 크기에 롤링 배포 중 동시에 실행될 인스턴스 수를 곱하고, 배치와 운영 작업의 연결도 더한다. DB가 처리할 수 있는 동시 작업 수는 `max_connections`보다 작을 수 있다. 연결 수를 늘렸을 때 실제 처리량과 대기가 어떻게 바뀌는지 측정한다. [MySQL 서버 시스템 변수](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html) · [Database Connections and Pooling](../interview/database-interview/05_database_connections_and_pooling.md)

## 서버와 풀의 상태를 같은 시간대에 본다

```sql
SELECT @@GLOBAL.max_connections, @@SESSION.wait_timeout;

SHOW GLOBAL STATUS WHERE Variable_name IN (
    'Threads_connected', 'Threads_running', 'Max_used_connections',
    'Aborted_connects', 'Aborted_clients', 'Connection_errors_max_connections'
);
```

- `Threads_connected`는 현재 열린 연결 수다. `Threads_running`은 `Sleep` 상태가 아닌 스레드 수이며, 잠금을 기다리는 작업도 포함할 수 있다. 두 지표를 실행 시간과 잠금 대기와 함께 본다. [MySQL 서버 상태 변수](https://dev.mysql.com/doc/refman/8.4/en/server-status-variables.html) · [MySQL 프로세스 상태](https://dev.mysql.com/doc/refman/8.4/en/thread-information.html)
- `Aborted_connects`는 연결 시도 실패, `Aborted_clients`는 연결된 클라이언트의 비정상 종료를 보는 데 사용한다. 누적값의 증가율과 앱의 커넥션 획득 실패 시각을 대조한다. [MySQL 연결 오류 진단](https://dev.mysql.com/doc/refman/8.4/en/communication-errors.html)
- 풀이 가득 찼다면 연결을 빌리는 데 걸린 시간과 빌린 뒤 보유한 시간을 나눈다. 보유 시간이 길어졌다면 느린 SQL, 유휴 트랜잭션, 반납 누락을 구분한다. [Database Connections and Pooling](../interview/database-interview/05_database_connections_and_pooling.md)

## 라이프사이클과 타임아웃을 맞춘다

서버의 `connect_timeout`은 접속 과정 중 연결 패킷을 기다리는 시간이고, `wait_timeout`은 비대화형 세션의 비활성 연결을 닫는 기준이다. 풀의 획득 대기 제한과 JDBC 소켓 타임아웃은 각기 다른 단계에 적용된다. 프록시나 서버가 유휴 연결을 먼저 끊는 환경에서는 풀의 유휴 연결 유지, 유효성 확인, 수명 정책을 함께 확인한다. JDBC에서 `try`-with-resources로 반환 경로를 보장하고, `SET` 등으로 세션 상태를 바꿨다면 다음 대여에 어떤 상태가 남는지 확인한다. [MySQL 서버 시스템 변수](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html) · [MySQL Connector/J 네트워킹 설정](https://dev.mysql.com/doc/connector-j/en/connector-j-connp-props-networking.html) · [HikariCP 풀 설정](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby)
