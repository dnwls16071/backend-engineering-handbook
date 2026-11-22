# Verifying Board Behavior and Read Performance

## 1. 실행하고 기능을 확인한다

Spring Boot·MySQL·Redis·Kafka로 로컬 실습을 실행했다. Java 테스트 8개와 게시글·댓글·좋아요·조회수·인기글을 묶은 HTTP 검증 시나리오가 통과했다. 같은 행을 대상으로 요청을 동시에 32건씩 보냈을 때 좋아요와 동일 사용자 조회수는 각각 한 건만 증가했다.

```text
Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
PASS post CRUD, exact decimal IDs, board counts, offset and keyset pagination
PASS two-level and nested comments, cross-post validation, tombstones, and count consistency
PASS 32 concurrent like and view retries produce one increment each, second viewer counts independently
PASS Kafka popularity and CQRS projections, idempotent unlike/delete, and deletion guard on cached reads
```

## 2. 브로커 중단과 재전송을 검증한다

Kafka가 멈춰도 좋아요 변경은 MySQL에 커밋됐고 미발행 아웃박스가 남았다. 재시작 뒤 큐가 처리됐고, 같은 이벤트를 다시 발행해 소비자 오프셋이 전진한 후에도 투영의 좋아요는 한 건이었다. 복구 시간은 브로커 재시작 명령 반환부터 투영과 발행 상태를 확인할 때까지다.

```text
PASS Kafka stopped: like write committed, outbox pending, CQRS projection remained unchanged
PASS Kafka restarted: pending event reached the CQRS projection (3.1s after start returned)
PASS replayed event advanced the Kafka offset without double-counting the like
```

## 3. 측정 조건과 실행 계획을 확인한다

Docker Desktop ARM64 VM은 12 vCPU와 약 7.65 GiB 메모리를 제공했다. 앱은 2 vCPU·768 MiB와 JDBC 풀 12개, k6는 2 vCPU·1 GiB와 최대 240 VU로 실행했다. MySQL 8.4.10에 게시글 20,000개를 넣고 601페이지의 20개 ID가 같은지 확인했다.

k6로 각 경로를 80회 워밍업한 뒤 250 req/s를 15초간 적용했다. 목록끼리는 동일 항목, 상세끼리는 동일 게시물을 비교했다. 두 번째 회차에서는 같은 데이터를 사용하여 실행 순서를 뒤집었다. 미시작은 k6가 VU를 할당하지 못해 HTTP 요청 자체를 시작하지 못한 횟수다. [Grafana k6 · Constant arrival rate](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/) · [Grafana k6 · Dropped iterations](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/)

MySQL `EXPLAIN ANALYZE`의 인덱스 반복자에서 OFFSET 경로는 12,020행을, 커서 경로는 21행을 처리했다. 커서의 추가 한 행은 다음 페이지 여부 확인에 쓰인다. [MySQL 8.4 · EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze)

## 4. 로컬 성능 결과를 해석한다

| 회차 | API 경로 | 완료 | HTTP 오류 | 미시작 | p95 (ms) | p99 (ms) | 투영 로더 호출 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 번호 목록 · OFFSET | 2,521 | 0 | 1,229 | 2,802.66 | 4,023.97 | — |
| 1 | 커서 목록 | 3,751 | 0 | 0 | 1.53 | 2.14 | — |
| 1 | 상세 · 직접 투영 | 3,751 | 0 | 0 | 1.47 | 2.14 | 3,751 |
| 1 | 상세 · 캐시와 요청 합치기 | 3,751 | 0 | 0 | 1.36 | 2.05 | 3 |
| 2 | 상세 · 캐시와 요청 합치기 | 3,751 | 0 | 0 | 1.31 | 2.10 | 3 |
| 2 | 상세 · 직접 투영 | 3,751 | 0 | 0 | 1.41 | 2.13 | 3,751 |
| 2 | 커서 목록 | 3,751 | 0 | 0 | 1.85 | 2.87 | — |
| 2 | 번호 목록 · OFFSET | 2,524 | 0 | 1,226 | 2,794.75 | 4,014.09 | — |

두 회차의 OFFSET 경로는 1,229·1,226건의 요청을 시작하지 못했다. 커서 경로는 두 회차 모두 미시작 0건이었다. 두 경로가 같은 행을 반환한다는 점과 실제 실행 계획을 함께 보면, 이 조건에서는 깊은 페이지의 앞부분을 건너뛰는 비용 차이가 컸다.

같은 상세 응답을 비교했을 때 투영 로더 호출은 직접 조회 3,751·3,751회에서 캐시 경로 3·3회로 줄었다. 두 회차 합계로 99.92% 감소했다. 이 수치는 캐싱과 같은 키 요청 합치기를 함께 적용한 투영 로더 계측값이다. 캐시 경로도 매번 MySQL에서 게시물이 살아 있는지 확인한다.

앱·부하 도구·저장소가 한 VM의 CPU와 메모리를 공유했다. 작은 합성 데이터와 한 게시글에 치우친 상세 조회는 실제 운영의 키 분포와 다르고, 이 실험에서는 조회와 같은 시간대의 대량 쓰기나 다중 노드 복제 부하를 가하지 않았다. 따라서 수치는 이 로컬 시나리오의 상대 비교에 적용한다.
