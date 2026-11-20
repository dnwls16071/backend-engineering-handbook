# Valkey Data Structures for Application Features

필요한 조회·갱신 형태에 맞춰 자료구조를 고른다. 아래 명령은 [단일 노드](01_valkey_fundamentals_and_command_execution.md)의 `vk`로 실행한다.

## 1. 장바구니와 세션

장바구니는 Hash의 필드를 상품 ID, 값을 수량으로 둘 수 있다. `HINCRBY` 한 번으로 수량을 바꾸고 `HDEL`로 항목을 제거한다. 수량이 0 이하가 되면 항목을 제거해야 하는 도메인 규칙은 증감과 함께 원자적으로 적용한다.

```bash
vk HSET lab:cart:42 sku-101 1 sku-205 2
vk HINCRBY lab:cart:42 sku-101 2
vk HGETALL lab:cart:42
vk HDEL lab:cart:42 sku-205
vk HSET lab:session:demo userId 42 device web
vk EXPIRE lab:session:demo 1800
vk HSET lab:session:demo device mobile
vk TTL lab:session:demo
```

String의 JSON 객체는 전체 교체가 간단하고 Hash는 필드 단위로 읽고 고치기 좋다. `HSET`으로 기존 Hash에 값을 쓰면 키 수준 TTL이 유지된다. 활동이 있을 때 세션의 수명을 다시 늘리는 정책이라면 `EXPIRE`를 별도로 실행한다. [Hashes](https://valkey.io/topics/hashes/) · [EXPIRE](https://valkey.io/commands/expire/)

## 2. 찜 목록과 기간별 인기 순위

Sorted Set은 멤버를 중복 없이 저장하고 점수 순으로 정렬한다. 찜 목록에서 점수를 등록 시각으로 사용하면 최근 찜부터 가져올 수 있다. `ZADD NX`는 이미 찜한 멤버의 등록 시각을 유지하고 `ZREM`은 찜을 취소한다.

```bash
vk ZADD lab:wishlist:42 NX 1700000000 sku-101 1700000120 sku-205
vk ZRANGE lab:wishlist:42 0 9 REV WITHSCORES
vk ZINCRBY lab:ranking:2026-11-20 1 sku-101
vk ZINCRBY lab:ranking:2026-11-20 3 sku-205
vk EXPIRE lab:ranking:2026-11-20 172800 NX
vk ZRANGE lab:ranking:2026-11-20 0 9 REV WITHSCORES
```

랭킹 키에 기간을 포함하면 날짜별 순위를 독립적으로 관리할 수 있다. 일별 키는 업무 시간대 기준으로 만들고, 기간이 끝난 뒤 보존 시각도 그 기준으로 정한다. 위 TTL은 첫 실행부터 48시간의 실습용 값이다. 한 멤버를 다시 저장하면 점수를 수정할 수 있으며, 점수가 같을 때는 멤버의 사전식 순서로 비교한다. `REV`에서는 동점 순서도 역순이다. [Sorted sets](https://valkey.io/topics/sorted-sets/) · [ZRANGE](https://valkey.io/commands/zrange/)

## 3. 최근 본 상품과 카운팅

List는 최근 조회 순서·중복을 그대로 유지하기에 좋다. `LPUSH`로 앞에 추가하고 `LTRIM`으로 크기를 제한한다. 목록에 상품별 최신 조회만 남기려면 Sorted Set에서 상품 ID를 멤버로 두고 시각 점수를 갱신한다.

```bash
docker exec -i valkey-lab valkey-cli --raw <<'COMMANDS'
MULTI
LPUSH lab:recent:42 sku-101 sku-205
LTRIM lab:recent:42 0 9
EXEC
LRANGE lab:recent:42 0 9
COMMANDS

vk INCR lab:views:sku-101
vk SADD lab:visitors:exact user-42 user-81 user-42
vk SCARD lab:visitors:exact
vk PFADD lab:visitors:approx user-42 user-81 user-42
vk PFCOUNT lab:visitors:approx
```

`INCR`은 이벤트 총량을, Set은 정확한 고유 방문자 수를 센다. HyperLogLog는 멤버 열거 없이 고유 수를 근사하는 용도다. 사용자 ID를 제한된 정수 오프셋으로 매핑할 수 있으면 Bitmap도 사용할 수 있다. 드문 값에 큰 오프셋이 붙으면 높은 위치까지 메모리가 할당될 수 있다. [Lists](https://valkey.io/topics/lists/) · [HyperLogLog](https://valkey.io/topics/hyperloglogs/) · [SETBIT](https://valkey.io/commands/setbit/)
