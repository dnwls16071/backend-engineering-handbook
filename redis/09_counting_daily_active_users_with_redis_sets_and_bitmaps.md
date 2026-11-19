# Counting Daily Active Users with Redis Sets and Bitmaps

DAU(Daily Active Users)는 서비스가 정한 날짜에 한 번 이상 방문한 고유 사용자 수다. 예제는 인증된 사용자의 방문을 기준으로 한다. 같은 사용자가 같은 날 여러 번 방문해도 한 명으로 센다. Redis Set과 Bitmap에 동일한 방문을 기록해 결과와 저장 방식의 차이를 비교한다.

## 1. Set으로 방문 사용자 기록하기

- `SADD`는 방문한 사용자 ID를 멤버로 추가하고, 새 멤버가 추가된 개수를 반환한다. 이미 기록한 ID를 다시 넣으면 `0`이다.
- `SMEMBERS`는 저장된 ID 전체를 반환한다. 결과에는 정해진 순서가 없다.
- `SCARD`는 멤버 수를 반환한다. DAU 숫자만 필요한 조회에는 `SCARD`를 사용한다.

비어 있는 실습용 Redis에서 11월 19일에 `user:101`, `user:205`, `user:101`이 차례로 방문한 상황을 재현한다.

```text
SADD lab:dau:set:2026-11-19 user:101
SADD lab:dau:set:2026-11-19 user:205
SADD lab:dau:set:2026-11-19 user:101
SMEMBERS lab:dau:set:2026-11-19
SCARD lab:dau:set:2026-11-19
```

`SADD`는 차례로 `1`, `1`, `0`을 반환한다. 두 사용자만 멤버로 남으므로 DAU는 `2`다.

**공식 문서** [Redis Sets](https://redis.io/docs/latest/develop/data-types/sets/) · [SADD](https://redis.io/docs/latest/commands/sadd/) · [SMEMBERS](https://redis.io/docs/latest/commands/smembers/) · [SCARD](https://redis.io/docs/latest/commands/scard/)

## 2. Bitmap으로 방문 여부 기록하기

Bitmap은 Redis String을 비트 단위로 다루는 방식이다. 사용자마다 고유한 정수 오프셋을 정하고 방문 시 그 위치의 비트를 `1`로 설정한다. 이미 `1`인 비트를 다시 `1`로 설정하면 방문자 수는 그대로다.

- `SETBIT key offset 1`은 방문을 기록하고 변경 전 비트 값을 반환한다.
- `GETBIT key offset`은 해당 사용자의 방문 여부를 읽는다. 문자열 범위 밖의 비트는 `0`으로 읽힌다.
- `BITCOUNT key`는 1인 비트의 개수를 세어 DAU를 반환한다.

예제에서는 사용자 번호를 0부터 시작하는 비트 오프셋으로 그대로 사용한다.

```text
SETBIT lab:dau:bitmap:2026-11-19 101 1
SETBIT lab:dau:bitmap:2026-11-19 205 1
SETBIT lab:dau:bitmap:2026-11-19 101 1
GETBIT lab:dau:bitmap:2026-11-19 101
GETBIT lab:dau:bitmap:2026-11-19 309
BITCOUNT lab:dau:bitmap:2026-11-19
```

`SETBIT`는 차례로 `0`, `0`, `1`을 반환한다. 방문한 사용자 101번은 `1`, 방문 기록이 없는 309번은 `0`이다. DAU는 Set 예제와 같은 `2`다.

**공식 문서** [Redis Bitmaps](https://redis.io/docs/latest/develop/data-types/strings/bitmaps/) · [SETBIT](https://redis.io/docs/latest/commands/setbit/) · [GETBIT](https://redis.io/docs/latest/commands/getbit/) · [BITCOUNT](https://redis.io/docs/latest/commands/bitcount/)

## 3. Set과 Bitmap 선택 기준

두 방식 모두 사용자마다 고유하게 기록하면 정확한 DAU를 얻을 수 있다.

| 기준 | Set | Bitmap |
| --- | --- | --- |
| 사용자 식별자 | UUID 등 문자열을 멤버로 그대로 사용한다. | 사용자와 비트 오프셋을 일대일로 연결한다. |
| 메모리에 영향을 주는 값 | 방문 사용자 수와 ID 길이 | 그날 기록한 가장 큰 오프셋 |
| 방문 여부 조회 | `SISMEMBER` | `GETBIT` |
| 전체 방문자 수 조회 | `SCARD`로 개수를 읽는다. 비용은 O(1)이다. | `BITCOUNT`로 문자열을 훑는다. 비용은 문자열 길이에 비례한다. |
| 방문한 ID 목록 | `SMEMBERS`로 조회한다. | 비트 위치를 찾아 사용자 ID로 변환해야 한다. |

번호가 촘촘한 정수 사용자 ID에는 Bitmap이 메모리 면에서 유리할 수 있다. Redis는 지정한 오프셋에 닿을 때까지 문자열을 늘린다. 예를 들어 가장 큰 오프셋이 `205`면 문자열 본문은 26바이트다. 그날 방문자가 적어도 큰 사용자 번호를 그대로 오프셋으로 쓰면 공간이 늘어난다. UUID를 쓰거나 사용자 번호가 넓은 범위에 드문드문 분포하면 Set이 간단하다.

**공식 문서** [SCARD 복잡도](https://redis.io/docs/latest/commands/scard/) · [SETBIT 오프셋과 할당](https://redis.io/docs/latest/commands/setbit/) · [BITCOUNT 복잡도](https://redis.io/docs/latest/commands/bitcount/)

## 4. 날짜별 키로 일간 집계 분리하기

집계 시간대를 정하고 방문을 기록한 시각을 그 시간대의 날짜로 변환해 키를 만든다. 예를 들어 `Asia/Seoul`을 기준으로 하면 자정 이후부터 다음 날짜 키에 쓴다. 동일한 사용자가 다른 날에도 방문하면 양쪽 날짜에서 각각 한 명으로 센다.

```text
SADD lab:dau:set:2026-11-20 user:101
SETBIT lab:dau:bitmap:2026-11-20 101 1
SCARD lab:dau:set:2026-11-19
SCARD lab:dau:set:2026-11-20
BITCOUNT lab:dau:bitmap:2026-11-19
BITCOUNT lab:dau:bitmap:2026-11-20
```

11월 19일 집계는 `2`, 11월 20일 집계는 `1`이다. API에서 날짜별 DAU를 조회할 때도 기록할 때와 같은 시간대로 날짜 키를 선택한다. [날짜별 Redis 키와 보관 기간](06_building_a_top_10_search_ranking_with_redis_sorted_sets.md)
