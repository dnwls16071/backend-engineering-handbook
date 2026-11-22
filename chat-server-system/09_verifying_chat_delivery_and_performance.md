# Verifying Chat Delivery and Performance

## 1. 실행 단위와 경계

단일 Spring Boot JAR을 두 인스턴스로 실행했다. Nginx가 WebSocket과 HTTP를 모두 전달했고 두 인스턴스는 PostgreSQL·Redis를 공유했다. 도메인, 저장, 실시간 전송, HTTP를 패키지로 분리한 배경은 [패키지 설계](02_structuring_chat_boundaries_in_one_application.md)에 정리했다.

## 2. 저장·브로드캐스트·장애 복구를 검증한다

Java 테스트 8개와 HTTP·WebSocket 통합 검증을 통과했다. 인스턴스 A에서 보낸 메시지를 인스턴스 B에서 받았고, 두 서버에 걸친 동시 쓰기 32건은 같은 방에서 연속 순번을 얻었다. 재접속 뒤 HTTP 이력으로 놓친 순번을 읽었다.

```text
Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
PASS room membership enforced for HTTP and WebSocket handshake
PASS raw WebSocket protocol, acknowledged persistence, cross-replica broadcast, and idempotent retry
PASS 32 concurrent writes through two replicas produce continuous sequence; Nginx reconnect replays the gap
PASS Nginx WebSocket upgrade and stub_status endpoint
```

Redis를 멈춘 상태에서도 발신자는 PostgreSQL 저장 ACK를 받았고 수신 측은 이력으로 메시지를 조회했다. 브로커를 다시 시작한 뒤 두 구독자가 등록된 상태에서 새 메시지로 실시간 전달 복구를 확인했다. 아래 시간은 재시작 명령의 반환부터 새 메시지 수신까지다. [Redis · Pub/Sub Delivery Semantics](https://redis.io/docs/latest/develop/pubsub/#delivery-semantics)

```text
PASS Redis stopped: sender received ACK and other replica recovered the message from PostgreSQL
PASS cross-replica broadcast recovered (1.2s after start returned)
```

## 3. 로컬 부하 측정 조건

Docker Desktop ARM64 VM은 12 vCPU와 약 7.65 GiB 메모리를 제공했다. 앱 인스턴스당 2 vCPU·768 MiB와 JDBC 커넥션 풀 12개, Nginx에는 1 vCPU·128 MiB, k6에는 2 vCPU·1 GiB를 적용했다. 측정 버전은 Nginx 1.30.7, PostgreSQL 18.7, Redis 7.4.12이다.

k6로 Nginx를 거쳐 한 방에 32개와 64개의 소켓을 연결하고 각 참여자가 초당 1개씩 12개 메시지를 보내도록 예약했다. 첫 회차는 32→64, 두 번째는 64→32 순서로 새 방과 참여자를 생성했다. 연결 준비 뒤 송신을 시작하고 종료 전에 2초를 두어 응답과 브로드캐스트를 수신했다. ACK 지연은 발신부터 ACK까지, 상대 수신 지연은 발신부터 다른 참여자의 이벤트 수신까지다. 송신과 수신 시간은 같은 k6 프로세스에서 밀리초 단위로 기록했다. [Grafana k6 · WebSockets](https://grafana.com/docs/k6/latest/using-k6/protocols/websockets/) · [Grafana k6 · Trend](https://grafana.com/docs/k6/latest/javascript-api/k6-metrics/trend/)

## 4. 측정 결과와 적용 범위

| 회차 | 연결 (A/B) | 송신 / ACK / 저장 | 상대 수신 / 예상 | ACK p95 / p99 (ms) | 수신 p95 / p99 (ms) | 오류 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 32 (16/16) | 384 / 384 / 384 | 11,904 / 11,904 | 7.00 / 10.00 | 8.00 / 11.00 | 0 |
| 1 | 64 (32/32) | 768 / 768 / 768 | 48,384 / 48,384 | 5.00 / 6.00 | 6.00 / 7.00 | 0 |
| 2 | 64 (32/32) | 768 / 768 / 768 | 48,384 / 48,384 | 11.65 / 40.33 | 13.00 / 44.00 | 0 |
| 2 | 32 (16/16) | 384 / 384 / 384 | 11,904 / 11,904 | 7.00 / 11.51 | 7.00 / 22.00 | 0 |

네 실행 모두 모든 참여자가 연결됐고 전송한 메시지가 ACK와 PostgreSQL 이력에 남았다. 각 발신자의 자기 수신을 제외한 상대방 수신 횟수도 예상치와 일치했다. 정상 실행에서의 계측 결과이며 Redis Pub/Sub의 전달 보장과 재연결 복구 범위는 별도로 판단한다. [Redis · Pub/Sub Delivery Semantics](https://redis.io/docs/latest/develop/pubsub/#delivery-semantics)

64개 연결의 상대 수신 p95는 6~13 ms였다. 두 번째 회차에서 상대 수신의 최대 지연은 32개 연결에서 138 ms, 64개 연결에서 162 ms였다. 짧은 두 회차의 결과에는 시도 간 편차가 있으며, 요청별 트레이스를 모으지 않아 긴 지연의 구체적인 원인은 확인 필요로 남긴다.

같은 Docker VM에서 앱·Nginx·저장소·부하 도구가 CPU와 메모리를 공유했다. 외부 네트워크와 TLS가 있는 운영 요청, 더 긴 연결 유지와 여러 방 분포, 장애 중의 부하는 이번 수치와 다른 조건이다. 이 결과는 동일한 로컬 시나리오에서 연결 수와 메시지 전달 규모를 비교하는 데 적용한다.
