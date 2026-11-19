# Redis Pub/Sub and Streams Messaging Patterns

Redis Pub/Sub으로 현재 접속한 화면에 주문 알림을 보내고, Redis Streams로 작업자가 나중에 처리할 주문 이벤트를 저장한다. 예제는 비어 있는 실습용 Redis에서 `redis-cli`로 실행한다. 미처리 이벤트를 가져오는 `XAUTOCLAIM`은 Redis 6.2 이상에서 사용할 수 있다.

| 기준 | Pub/Sub | Streams |
| --- | --- | --- |
| 전송 단위 | 채널에 메시지를 발행한다. | Stream 키에 ID가 있는 엔트리를 추가한다. |
| 수신 대상 | 발행 시점에 채널을 구독 중인 클라이언트가 각각 받는다. | 소비자가 ID를 기준으로 읽거나 Consumer Group 안에서 분담한다. |
| 연결이 끊겼을 때 | 끊긴 동안의 메시지를 다시 받을 수 없다. | 보관 중인 엔트리는 다시 읽을 수 있다. 그룹에서는 아직 확인되지 않은 작업도 회수할 수 있다. |
| 주문 서비스 예시 | 접속 중인 관리자 화면에 새 주문을 표시한다. | 주문 이벤트를 결제와 배송 작업에서 각각 소비한다. |

## 1. Pub/Sub · 접속 중인 구독자에게 실시간 전달

`SUBSCRIBE`로 채널을 구독하고, 다른 클라이언트에서 `PUBLISH`로 메시지를 보낸다. 실습은 같은 Redis에 연결한 터미널 두 개에서 진행한다.

터미널 A에서 구독한다.

```text
SUBSCRIBE lab:orders:notifications
```

구독 응답이 표시되면 터미널 B에서 주문 알림을 발행한다.

```text
PUBLISH lab:orders:notifications '{"order_id":101,"status":"created"}'
```

터미널 A에는 채널 이름과 주문 메시지가 출력된다. 두 구독자가 접속해 있다면 같은 알림을 각각 받는다. `PUBLISH`의 반환값은 메시지를 전달한 클라이언트 수다. 구독자가 없으면 단일 Redis 인스턴스에서 `0`이 반환된다.

Pub/Sub의 전달 방식은 at-most-once다. 구독자가 끊겨 있거나 메시지를 처리하는 중 오류가 발생하면 Redis가 그 메시지를 다시 보내지 않는다. 일시적인 화면 갱신처럼 연결이 복구된 후 원본 상태를 다시 조회할 수 있는 알림에 맞는다.

**공식 문서** [Redis Pub/Sub 전달 방식](https://redis.io/docs/latest/develop/pubsub/#delivery-semantics) · [SUBSCRIBE](https://redis.io/docs/latest/commands/subscribe/) · [PUBLISH](https://redis.io/docs/latest/commands/publish/)

## 2. Streams · 주문 이벤트를 저장하고 읽기

Streams의 각 엔트리는 ID와 필드·값 쌍으로 구성된다. `XADD`로 저장하고 `XRANGE`로 ID 범위를 조회한다. 예제는 이후 명령에서 그대로 쓸 수 있도록 ID를 직접 지정한다. 보통은 `XADD lab:orders:events * ...`로 Redis에 ID 생성을 맡긴다.

```text
XADD lab:orders:events 1-0 order_id 101 status created
XADD lab:orders:events 2-0 order_id 102 status created
XRANGE lab:orders:events - +
XREAD COUNT 1 STREAMS lab:orders:events 0-0
```

`XRANGE`는 두 엔트리를 ID 순서로 반환한다. `XREAD`는 지정한 ID보다 큰 엔트리부터 읽으므로 위 명령은 `1-0`을 받는다. 다음 `XREAD`에 `1-0`을 넘기면 `2-0`부터 이어서 읽는다. 새 이벤트를 기다리는 소비자는 `BLOCK`에 밀리초 단위 대기 시간을 줄 수 있다.

**공식 문서** [Redis Streams 개요](https://redis.io/docs/latest/develop/data-types/streams/) · [XADD](https://redis.io/docs/latest/commands/xadd/) · [XREAD](https://redis.io/docs/latest/commands/xread/) · [XRANGE](https://redis.io/docs/latest/commands/xrange/)

## 3. Consumer Group · 작업 분담과 재처리

같은 그룹의 여러 워커는 새 엔트리를 나눠 읽는다. 결제와 배송처럼 두 기능이 모든 이벤트를 각각 처리해야 한다면 그룹을 따로 만든다. 각 그룹은 전달 위치와 미확인 엔트리 목록인 PEL(Pending Entries List)을 별도로 관리한다.

```text
XGROUP CREATE lab:orders:events billing 0
XREADGROUP GROUP billing worker-a COUNT 1 STREAMS lab:orders:events >
XPENDING lab:orders:events billing
XACK lab:orders:events billing 1-0
```

- `XGROUP CREATE ... 0`은 그룹이 기존 엔트리부터 읽도록 한다. 그룹을 만들 때 `$`를 사용하면 생성 이후의 새 엔트리부터 읽는다.
- `XREADGROUP`의 `>`는 해당 그룹에서 아직 전달되지 않은 엔트리를 읽는다. 위에서는 `1-0`이 `worker-a`에 배정되고 `XPENDING`에 나타난다.
- 업무 처리가 성공한 뒤 `XACK`을 실행한다. ACK는 해당 그룹의 PEL에서 엔트리를 제거한다. 같은 엔트리는 Stream에 보관되어 있는 동안 `XRANGE`로 계속 조회할 수 있다.

다음은 `worker-a`가 두 번째 엔트리를 받은 뒤 ACK를 보내기 전에 중단된 상황을 재현한다.

```text
XREADGROUP GROUP billing worker-a COUNT 1 STREAMS lab:orders:events >
XPENDING lab:orders:events billing
```

두 번째 엔트리 `2-0`을 읽은 뒤 **5초 이상 기다리고**, `worker-b`가 오래 미확인 상태인 작업을 가져온다.

```text
XAUTOCLAIM lab:orders:events billing worker-b 5000 0-0 COUNT 10
XPENDING lab:orders:events billing - + 10
```

`XAUTOCLAIM` 응답에서 `2-0`을 받고, `XPENDING` 상세 조회에서 소유자가 `worker-b`로 바뀐 것을 확인한다. 처리에 성공했다고 가정하고 아래 명령으로 확인한다.

```text
XACK lab:orders:events billing 2-0
XPENDING lab:orders:events billing
XRANGE lab:orders:events - +
```

`XPENDING`의 미확인 건수는 `0`이고 `XRANGE`에는 두 엔트리가 남는다. 워커가 업무 처리를 끝냈지만 ACK 전에 종료될 수 있으므로, 회수한 이벤트를 다시 처리할 때 중복 부작용이 생기지 않도록 이벤트 ID를 기록한다. 미확인 경과 시간은 정상적으로 오래 걸리는 작업을 회수하지 않도록 처리 시간에 맞춘다.

**공식 문서** [XGROUP CREATE](https://redis.io/docs/latest/commands/xgroup-create/) · [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/) · [XPENDING](https://redis.io/docs/latest/commands/xpending/) · [XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/) · [XACK](https://redis.io/docs/latest/commands/xack/)

## 4. Streams의 보관 정책

이벤트가 계속 쌓이면 `XADD ... MAXLEN ~ 10000`이나 `XTRIM`으로 보관량을 제한할 수 있다. `~`는 정확한 개수보다 트리밍 효율을 우선하는 옵션이다. 너무 일찍 트리밍하면 늦게 따라오는 그룹이나 미확인 작업의 원본을 잃을 수 있으므로, 재처리 기간과 소비 지연을 기준으로 보관량을 정한다. Redis 재시작 후 데이터가 얼마나 복구되는지는 RDB나 AOF 등 영속화 설정에 따라 달라진다.

**공식 문서** [XTRIM](https://redis.io/docs/latest/commands/xtrim/) · [Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
