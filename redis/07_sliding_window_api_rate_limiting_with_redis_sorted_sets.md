# Sliding Window API Rate Limiting with Redis Sorted Sets

사용자별로 검색 API를 최근 10초 동안 최대 5회 호출할 수 있도록 제한한다. Redis Sorted Set에 허용한 요청의 시각을 기록하고, 매 요청마다 오래된 기록을 제거한 뒤 새 요청의 허용 여부를 결정한다.

## 1. 요청 기록을 정리하는 Sorted Set 명령

| 명령 | 요청 제한에서의 역할 |
| --- | --- |
| `ZREMRANGEBYSCORE key -inf cutoff` | 점수가 기준 시각 이하인 요청 기록을 제거한다. |
| `ZCARD key` | 현재 남아 있는 요청 기록 수를 반환한다. 키가 없으면 `0`이다. |
| `EXPIRE key 10` | 마지막으로 허용한 요청에서 10초가 지나면 키 전체가 만료되도록 설정한다. |

다음은 현재 시각이 `11000`밀리초라고 가정해 명령을 따로 살펴보는 예제다. 실습용 Redis의 `redis-cli`에서 실행한다.

```text
ZADD lab:rate:demo 1000 req-a 2000 req-b 11000 req-c
ZREMRANGEBYSCORE lab:rate:demo -inf 1000
ZCARD lab:rate:demo
EXPIRE lab:rate:demo 10
```

10초 전 경계에 있는 `req-a`가 지워지고, 두 요청이 남는다. 실제 구현은 Sorted Set의 점수에 요청 시각을 넣고, 멤버에는 애플리케이션이 생성한 고유 요청 ID를 넣는다. 같은 밀리초에 요청이 여러 건 도착해도 각각 기록할 수 있다.

**공식 문서** [ZREMRANGEBYSCORE](https://redis.io/docs/latest/commands/zremrangebyscore/) · [ZCARD](https://redis.io/docs/latest/commands/zcard/) · [EXPIRE](https://redis.io/docs/latest/commands/expire/)

## 2. 최근 10초를 기준으로 허용 여부 결정하기

슬라이딩 윈도우는 각 요청이 들어온 시각을 기준으로 범위를 다시 계산한다. 지금 시각을 `now`라고 하면 점수가 `(now - 10000, now]` 범위에 있는 기록을 센다. 정확히 10초 전에 허용한 요청은 범위에서 빠진다.

1. Redis의 `TIME`으로 현재 시각을 읽는다.
2. 10초 전과 그 이전에 허용한 요청 기록을 삭제한다.
3. 남은 기록이 5개 이상이면 제한 응답을 반환한다. 가장 오래된 기록이 범위에서 빠지는 시각으로 재시도 대기 시간을 계산한다.
4. 남은 기록이 5개보다 적으면 새 요청을 기록하고 키의 만료 시간을 10초로 갱신한다.

재고를 확인하고 차감하는 예제처럼, 기록 수를 읽은 뒤 기록을 추가하기까지의 연산을 원자적으로 처리한다. 예를 들어 이미 4건이 기록된 상태에서 두 요청이 동시에 `ZCARD` 결과 `4`를 읽으면, 각각 새 기록을 넣어 한도를 넘길 수 있다. Lua 스크립트는 삭제, 개수 확인, 추가를 한 번에 실행한다. [재고 예제의 확인과 차감](05_preventing_inventory_race_conditions_with_redis.md)

**공식 문서** [Redis 요청 제한](https://redis.io/docs/latest/develop/use-cases/rate-limiter/) · [Redis TIME](https://redis.io/docs/latest/commands/time/) · [Lua 스크립트의 원자 실행](https://redis.io/docs/latest/develop/programmability/eval-intro/)

## 3. Lua로 정책을 실행하고 API 응답으로 연결하기

다음 내용을 `rate_limit.lua`로 저장한다. 반환값의 순서는 허용 여부, 남은 요청 횟수, 재시도 대기 시간(밀리초)이다.

```lua
local key = KEYS[1]
local request_id = ARGV[1]
local window_seconds = 10
local window_ms = window_seconds * 1000
local limit = 5

if not request_id or request_id == "" then
    return redis.error_reply("ERR request ID is required")
end

local time = redis.call("TIME")
local now_ms = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)

redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms - window_ms)
local count = redis.call("ZCARD", key)

if count >= limit then
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    local retry_after_ms = tonumber(oldest[2]) + window_ms - now_ms
    return {0, 0, retry_after_ms}
end

if redis.call("ZADD", key, "NX", now_ms, request_id) == 0 then
    return redis.error_reply("ERR request ID was already used")
end

redis.call("EXPIRE", key, window_seconds)
return {1, limit - count - 1, 0}
```

빈 실습용 Redis에 연결해 6건을 연속으로 보낸다. Redis가 기본 주소나 포트와 다르면 `redis-cli`에 접속 옵션을 지정한다.

```sh
for request_id in req-1 req-2 req-3 req-4 req-5 req-6; do
    redis-cli --json --eval rate_limit.lua lab:rate:search:user-42 , "$request_id"
done
```

10초 안에 실행하면 처음 다섯 요청은 허용되고 남은 횟수는 `4`에서 `0`으로 줄어든다. 여섯 번째 요청은 `[0, 0, 재시도까지 남은 밀리초]`를 반환한다. 첫 요청이 10초 범위를 벗어나면 다음 요청을 허용할 수 있다. 거절한 요청은 기록하거나 TTL을 갱신하지 않는다.

API에서는 인증된 사용자 ID와 API 이름을 키에 포함하고, 실제 비즈니스 로직을 실행하기 전에 이 스크립트를 호출한다. 제한을 넘으면 HTTP `429 Too Many Requests`를 응답하고, `Retry-After`에 대기 시간을 초 단위로 올림해 넣을 수 있다. 허용 횟수는 제한기를 통과한 요청을 기준으로 센다.

**공식 문서** [Redis CLI의 Lua 실행](https://redis.io/docs/latest/develop/tools/cli/#run-lua-scripts) · [HTTP 429](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) · [Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after)
