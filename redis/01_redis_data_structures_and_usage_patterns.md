# Redis Data Structures and Usage Patterns

Redis에서는 필요한 연산을 기준으로 자료구조를 고른다. 값 전체를 읽고 쓰거나 횟수를 세려면 String, 순서대로 쌓인 항목을 꺼내려면 List, 중복 없이 소속 여부를 검사하려면 Set을 사용한다. 점수를 기준으로 순위를 조회할 때는 Sorted Set, 한 객체의 필드를 따로 읽거나 바꿀 때는 Hash가 적합하다.

아래 명령은 비어 있는 실습용 Redis에서 `redis-cli`로 실행한다. `ZRANGE ... REV`가 포함된 예제는 Redis 6.2 이상을 기준으로 한다.

## 1. String · 값 저장과 만료

String은 텍스트, 직렬화한 JSON, 바이너리 데이터를 값 하나로 저장한다. 정수 문자열은 카운터 명령으로 증가시킬 수 있다. JSON을 String으로 저장하면 Redis는 그 내용을 값 전체로 다루므로, 필드 하나만 바꿀 때도 애플리케이션에서 역직렬화하고 새 값을 저장해야 한다.

```text
SET lab:message "hello redis" EX 60
GET lab:message
TTL lab:message
```

`SET ... EX 60`은 값을 저장하는 명령에 60초 만료를 함께 설정한다. 일반 `SET`으로 기존 키를 덮어쓰면 TTL이 제거된다. 이전 TTL을 유지하려면 `KEEPTTL`을 사용한다. `TTL`의 `-1`은 만료 시간이 없는 키, `-2`는 존재하지 않는 키를 뜻한다.

**공식 문서** [Redis Strings](https://redis.io/docs/latest/develop/data-types/strings/) · [SET](https://redis.io/docs/latest/commands/set/) · [TTL](https://redis.io/docs/latest/commands/ttl/)

## 2. String 활용 · 동시성 제어와 캐시

### 카운터와 조건부 등록

두 요청이 같은 값 `10`을 읽은 뒤 각자 `11`을 저장하면 증가 한 번이 사라진다. 단일 키의 증가는 그 연산을 원자적으로 수행하는 `INCR` 또는 `INCRBY`로 처리한다.

```text
SET lab:views:42 0
INCR lab:views:42
INCRBY lab:views:42 4
GET lab:views:42
```

결과는 `5`다. 여러 명령에 걸쳐 조건을 확인하고 값을 변경해야 한다면, 데이터가 달라졌을 때 재시도하는 `WATCH`와 `MULTI/EXEC` 또는 짧은 Lua 스크립트 등으로 연산 범위를 묶는다.

```text
SET lab:job:claim:42 worker-a NX EX 30
SET lab:job:claim:42 worker-b NX EX 30
GET lab:job:claim:42
```

`NX`는 키가 없을 때만 저장하고, `EX`는 등록을 30초 후 만료시킨다. 두 번째 등록은 거절되고 키에는 `worker-a`가 남는다. 유효 기간이 끝나면 다른 워커가 다시 등록할 수 있다. 작업 완료와 재처리 여부는 업무 데이터의 멱등성 규칙으로 관리한다.

### Cache-Aside 읽기와 무효화

1. 먼저 `GET`으로 캐시를 읽는다.
2. 캐시에 값이 없으면 원본 DB를 조회한 뒤 `SET ... EX`로 결과를 저장한다.
3. 원본 데이터 변경이 커밋되면 해당 캐시 키를 삭제한다. 다음 읽기에서 갱신된 데이터를 다시 채운다.

아래의 JSON은 DB에서 상품을 조회했다고 가정한 예시 값이다.

```text
GET lab:cache:product:42
SET lab:cache:product:42 '{"name":"Keyboard","price":50000}' EX 120
GET lab:cache:product:42
DEL lab:cache:product:42
GET lab:cache:product:42
```

캐시 미스에서는 값이 없고, 저장 후에는 JSON을 읽을 수 있다. 삭제 후 다시 캐시 미스가 난다. DB 변경과 캐시 삭제는 별도 연산이다. 갱신 전 데이터를 읽은 요청이 삭제 이후에 캐시를 채울 수도 있으므로, 허용할 데이터 지연에 맞춰 TTL과 무효화 전략을 정한다.

**공식 문서** [INCR](https://redis.io/docs/latest/commands/incr/) · [Redis 트랜잭션](https://redis.io/docs/latest/develop/using-commands/transactions/) · [Cache-Aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/)

## 3. List · 순서가 있는 작업 큐

List에는 순서가 있고 같은 값을 여러 번 저장할 수 있다. `LPUSH`로 왼쪽에 넣고 `RPOP`으로 오른쪽에서 꺼내면 먼저 넣은 작업을 먼저 처리하는 FIFO가 된다.

```text
LPUSH lab:queue:emails job-1 job-2
LRANGE lab:queue:emails 0 1
RPOP lab:queue:emails
LLEN lab:queue:emails
```

조회하면 왼쪽부터 `job-2`, `job-1`이 나오고, `RPOP`은 `job-1`을 꺼낸다. 빈 큐에서 새 작업을 기다릴 때는 `BRPOP`을 쓸 수 있다. 꺼낸 후 처리 도중 워커가 종료되는 경우까지 고려한다면 `LMOVE`로 작업을 처리 중인 목록에 옮기고, 완료 확인과 재처리 정책을 둔다.

**공식 문서** [Redis Lists](https://redis.io/docs/latest/develop/data-types/lists/) · [LMOVE](https://redis.io/docs/latest/commands/lmove/)

## 4. Set · 중복 제거와 집합 연산

Set은 순서를 보장하지 않는 고유 원소 집합이다. 상품 태그, 참여자 식별자, 권한 목록처럼 소속 여부나 교집합이 필요한 경우에 쓴다.

```text
SADD lab:tags:42 redis cache cache
SADD lab:tags:43 redis backend
SISMEMBER lab:tags:42 cache
SCARD lab:tags:42
SINTER lab:tags:42 lab:tags:43
```

중복으로 넣은 `cache`는 한 번만 저장된다. 태그 개수는 `2`이고, 두 상품의 공통 태그는 `redis`다. 집합이 커서 전체를 한 번에 응답받기 부담스러우면 `SSCAN`으로 나누어 조회한다.

**공식 문서** [Redis Sets](https://redis.io/docs/latest/develop/data-types/sets/) · [SINTER](https://redis.io/docs/latest/commands/sinter/)

## 5. Sorted Set · 점수와 순위

Sorted Set은 각 고유 멤버에 점수를 부여한다. 같은 멤버에 `ZADD`를 다시 실행하면 점수가 갱신되고, `ZINCRBY`로 기존 점수에 값을 더할 수 있다.

```text
ZADD lab:leaderboard 110 alice 120 bob 100 chris
ZINCRBY lab:leaderboard 25 alice
ZRANGE lab:leaderboard 0 1 REV WITHSCORES
ZREVRANK lab:leaderboard alice
```

상위 두 명은 `alice 135`, `bob 120`이다. `ZRANGE`의 범위 인덱스는 0부터 시작하며 끝 인덱스를 포함한다. `ZREVRANK`에서 1위의 반환값은 `0`이다. 점수가 같을 때는 멤버 값을 바이트 기준 사전식 순서로 비교하며 `REV` 조회에서는 그 순서도 반대가 된다.

**공식 문서** [Redis Sorted Sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/) · [ZRANGE](https://redis.io/docs/latest/commands/zrange/) · [ZREVRANK](https://redis.io/docs/latest/commands/zrevrank/)

## 6. Hash · 객체의 필드 단위 읽기와 변경

Hash는 키 하나 아래에 필드 이름과 값을 저장한다. 상품의 이름, 가격, 조회 수처럼 함께 조회하되 필드별로 변경할 수 있는 데이터를 표현하기 좋다.

```text
HSET lab:product:42 name Keyboard price 50000 views 0
HGET lab:product:42 name
HMGET lab:product:42 name price
HINCRBY lab:product:42 views 1
```

`HMGET`으로 필요한 필드만 읽고, `HINCRBY`로 조회 수만 `1`로 바꾼다. `EXPIRE`는 Hash 키 전체에 적용된다. Redis 7.4 이상에서는 `HEXPIRE`로 특정 필드에도 만료 시간을 줄 수 있다.

**공식 문서** [Redis Hashes](https://redis.io/docs/latest/develop/data-types/hashes/) · [HMGET](https://redis.io/docs/latest/commands/hmget/) · [HEXPIRE](https://redis.io/docs/latest/commands/hexpire/)
