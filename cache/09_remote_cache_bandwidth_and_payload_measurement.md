# Remote Cache Bandwidth and Payload Measurement

원격 Redis 캐시로 원본 조회를 줄이면 네트워크 전송과 직렬화 비용이 다음 병목이 될 수 있다. 적중률과 함께 응답 크기, 전송률, 지연을 측정한다.

## 1. 캐시 어사이드로 원격 캐시 붙이기

읽기 요청은 Redis에서 먼저 조회한다. 값이 없으면 원본 DB에서 읽은 뒤 직렬화한 값에 TTL을 부여해 저장한다. 쓰기는 원본 저장이 커밋된 뒤 캐시를 무효화하거나 새 버전으로 갱신한다. 캐시 장애 동안 원본 호출량이 얼마나 늘어나는지도 계측한다. 캐시 키에는 테넌트나 조회 조건처럼 결과를 바꾸는 요소를 포함한다. [Spring Boot와 Redis 캐시](02_springboot_caching_with_redis.md) · [Cache-Aside 패턴](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 2. 응답 크기로 대역폭 예상하기

GET 적중만 따로 보면 값의 전송량은 초당 적중 건수와 평균 값 크기의 곱으로 근사할 수 있다. 초당 2,000건이 각각 200KiB를 반환하면 값만 약 391MiB/s다. 응답을 20KiB로 줄이면 약 39MiB/s다. 실제 전송에는 요청, 프로토콜, 연결 암호화, 응답 구성에 따른 추가 비용이 있다. 파이프라이닝은 왕복 횟수를 줄일 수 있지만 같은 값을 반환한다면 값 바이트도 전송된다. [Redis 파이프라이닝](https://redis.io/docs/latest/develop/using-commands/pipelining/)

## 3. 키의 저장 크기와 응답 크기 분포 재기

| 측정 | 의미 |
| --- | --- |
| `MEMORY USAGE key` | Redis에 키와 값을 보관하는 데 필요한 메모리 크기다. 자료형에 따라 일부 원소를 표본으로 사용한다. |
| `STRLEN key` | 문자열 값 자체의 바이트 수다. 메모리 오버헤드와 프로토콜을 제외한다. |
| 클라이언트의 응답 바이트 | 실제 호출이 반환한 값을 센다. 같은 정렬 집합이라도 상위 10건 조회와 전체 조회의 크기가 다르다. |

폐기 가능한 로컬 Redis의 소켓을 `CACHE_LAB_SOCKET`으로 지정하고 아래 실습을 실행한다. 2KiB와 200KiB의 문자열을 저장해 값의 길이와 메모리 크기를 비교한다. [Redis MEMORY USAGE](https://redis.io/docs/latest/commands/memory-usage/) · [Redis STRLEN](https://redis.io/docs/latest/commands/strlen/)

```sh
: "${CACHE_LAB_SOCKET:?Set the socket path of a disposable Redis instance}"
printf '%2048s' x | redis-cli -s "$CACHE_LAB_SOCKET" -x SET cache-lab:small
printf '%204800s' x | redis-cli -s "$CACHE_LAB_SOCKET" -x SET cache-lab:large
redis-cli -s "$CACHE_LAB_SOCKET" STRLEN cache-lab:small
redis-cli -s "$CACHE_LAB_SOCKET" STRLEN cache-lab:large
redis-cli -s "$CACHE_LAB_SOCKET" MEMORY USAGE cache-lab:large
```

`redis-cli --memkeys`는 SCAN으로 키 공간을 순회하고 메모리 기준으로 큰 키를 찾는다. 요청이 반환하는 페이로드의 분포는 애플리케이션에서 p50·p95·p99를 별도로 기록한다. Redis Cluster에서 노드 편차를 찾으려면 각 샤드의 결과를 따로 확인한다. [Redis CLI 키 크기 스캔](https://redis.io/docs/latest/develop/tools/cli/)

## 4. 같은 측정 창에서 변경 전후 비교하기

같은 데이터와 요청 구성으로 워밍업을 마친 뒤 동일한 길이의 창을 비교한다. 각 창의 시작과 끝에서 `INFO stats`의 `total_net_output_bytes`를 읽고 차이를 초로 나눠 노드 전송률을 구한다. 같은 노드와 프로세스의 카운터를 사용하고, 재시작이나 리셋이 확인되면 창을 새로 잡는다. 이 값은 노드 전체 값이므로 다른 트래픽을 분리하려면 애플리케이션의 키 유형별 응답 바이트도 함께 본다. [Redis INFO](https://redis.io/docs/latest/commands/info/)

```sh
: "${CACHE_LAB_SOCKET:?Set the socket path of a disposable Redis instance}"
redis-cli -s "$CACHE_LAB_SOCKET" INFO stats | grep -E '^(total_net_output_bytes|keyspace_hits|keyspace_misses):'
```

전송률, 요청당 바이트, Redis 적중률과 원본 조회 수, 응답 p95·p99를 함께 비교한다. 요청 구성이 달라지면 전송률만으로 개선 여부를 해석하기 어렵다.

## 5. 압축과 분할의 효과와 한계 판단하기

압축은 같은 데이터를 적은 바이트로 보낼 수 있지만 CPU, 압축 해제 지연, 형식 변경 비용을 추가한다. 분할이 효과적인 경우는 호출이 일부 조각만 읽어도 될 때다. 매번 모든 조각을 모으면 전체 데이터는 여전히 전송되고 키 요청도 늘어난다. 목록과 상세의 필요 필드를 나누고, 페이지나 집계 결과만 읽게 한 뒤 실제 직렬화 바이트와 지연을 다시 비교한다.
