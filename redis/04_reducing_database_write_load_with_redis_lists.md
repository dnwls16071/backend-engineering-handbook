# Reducing Database Write Load with Redis Lists

좋아요 요청이 몰릴 때 요청마다 DB에 접속해서 같은 게시물의 카운터를 갱신하면 쓰기 트랜잭션과 행 경합이 늘어난다. Redis List에 좋아요 추가 이벤트를 모으고, 워커가 배치 단위로 DB에 반영하면 요청 경로와 DB 쓰기를 분리할 수 있다. 아래 예제는 Redis 6.2 이상 단일 인스턴스와 실습용 PostgreSQL을 사용한다.

## 1. 필요한 연산으로 자료구조 고르기

좋아요 데이터를 어떻게 사용할지 먼저 정하면 필요한 자료구조가 좁혀진다. 카운터만 증가시키려면 String의 `INCR`이 간단하다. 각 요청의 사용자와 게시물을 보존해 워커가 순서대로 처리하려면 List를 사용할 수 있다. 여러 소비자 그룹의 진행 위치와 미확인 작업을 관리하려면 Streams를 고려한다. [Redis 자료구조](01_redis_data_structures_and_usage_patterns.md) · [Pub/Sub과 Streams](02_redis_pub_sub_and_streams_messaging_patterns.md)

| List 명령 | 작업 큐에서의 역할 |
| --- | --- |
| `RPUSH` | 새 이벤트를 리스트 오른쪽에 추가한다. |
| `LRANGE` | 지정한 인덱스 범위를 조회한다. 끝 인덱스도 포함하며, 확인한 이벤트는 그대로 남는다. |
| `LPOP` | 왼쪽의 첫 이벤트를 반환하면서 제거한다. 오른쪽에 넣고 왼쪽에서 꺼내면 FIFO가 된다. |

```text
RPUSH lab:likes:list-demo e-1 e-2
LRANGE lab:likes:list-demo 0 1
LPOP lab:likes:list-demo
LRANGE lab:likes:list-demo 0 -1
```

첫 조회에는 `e-1`과 `e-2`가 나오고, `LPOP` 이후에는 `e-2`만 남는다. DB 쓰기 워커가 `LPOP` 직후 종료되면 꺼낸 이벤트를 복구하기 어렵다. 처리 완료까지 이벤트를 보관하려면 `LMOVE`로 대기 목록에서 처리 중인 목록으로 옮긴다.

**공식 문서** [Redis Lists](https://redis.io/docs/latest/develop/data-types/lists/) · [LRANGE](https://redis.io/docs/latest/commands/lrange/) · [LPOP](https://redis.io/docs/latest/commands/lpop/) · [LMOVE](https://redis.io/docs/latest/commands/lmove/)

## 2. 좋아요 이벤트를 모아 워커에 배정하기

요청을 받은 애플리케이션은 `event_id`, `post_id`, `user_id`를 담은 이벤트를 `ready` 목록에 넣는다. 워커는 최대 배치 크기나 대기 시간 기준에 따라 이벤트를 모아 반영한다. API가 등록 직후 응답한다면 그 응답의 의미는 접수이며, DB에서 조회한 좋아요 수는 워커가 반영할 때 갱신된다.

```text
RPUSH lab:likes:ready '{"event_id":"e-1","post_id":42,"user_id":101}'
RPUSH lab:likes:ready '{"event_id":"e-2","post_id":42,"user_id":102}'
LRANGE lab:likes:ready 0 -1

LMOVE lab:likes:ready lab:likes:processing LEFT RIGHT
LMOVE lab:likes:ready lab:likes:processing LEFT RIGHT
LRANGE lab:likes:processing 0 -1
```

`LMOVE`는 대기 목록의 왼쪽에서 이벤트를 꺼내 처리 목록의 오른쪽으로 원자적으로 옮긴다. 이 시점에 두 이벤트는 `processing`에 남아 있다. 실습은 워커 한 대를 가정한다. 운영에서 여러 워커를 사용한다면 처리 중인 이벤트의 소유자와 남은 유효 시간을 기록해 회수 대상을 구분한다.

**공식 문서** [RPUSH](https://redis.io/docs/latest/commands/rpush/) · [LMOVE의 처리 목록 패턴](https://redis.io/docs/latest/commands/lmove/)

## 3. 배치로 저장하고 게시물별 카운터 갱신하기

사용자 한 명은 같은 게시물에 좋아요를 한 번만 추가할 수 있다고 가정한다. `post_likes`의 복합 기본 키로 이 조건을 표현하고, `post_like_counts`에는 게시물별 집계 결과를 둔다.

```sql
CREATE TABLE post_likes (
    post_id bigint NOT NULL,
    user_id bigint NOT NULL,
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE post_like_counts (
    post_id bigint PRIMARY KEY,
    like_count bigint NOT NULL
);
```

워커가 Redis에서 꺼낸 두 이벤트의 `post_id`와 `user_id`를 `VALUES`에 넣었다고 가정한다. 새로 저장된 좋아요만 `RETURNING`으로 받고, 게시물별로 묶어 카운터를 한 번씩 갱신한다. 좋아요 행과 카운터는 같은 SQL 문으로 반영된다.

```sql
WITH inserted AS (
    INSERT INTO post_likes (post_id, user_id)
    VALUES (42, 101), (42, 102)
    ON CONFLICT (post_id, user_id) DO NOTHING
    RETURNING post_id
)
INSERT INTO post_like_counts (post_id, like_count)
SELECT post_id, count(*)
FROM inserted
GROUP BY post_id
ON CONFLICT (post_id)
DO UPDATE SET like_count = post_like_counts.like_count + EXCLUDED.like_count;

SELECT like_count FROM post_like_counts WHERE post_id = 42;
```

빈 실습 테이블에서 처음 실행하면 `2`가 나온다. 같은 배치를 다시 실행하면 새로 삽입되는 좋아요가 없어 `2`가 유지된다. 이 방식은 여러 요청의 DB 왕복을 묶고, 같은 게시물의 카운터 갱신 횟수를 배치당 한 번으로 줄인다.

**공식 문서** [PostgreSQL INSERT, ON CONFLICT, RETURNING](https://www.postgresql.org/docs/current/sql-insert.html) · [데이터를 변경하는 WITH 절](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-MODIFYING)

## 4. DB 커밋 이후 확인하고 중단된 작업 회수하기

DB 커밋이 끝나면 `LREM`으로 처리 목록에서 해당 이벤트를 제거한다. 같은 JSON 문자열을 써야 하므로 워커는 Redis에서 받은 원본 값을 보관한다.

첫 번째 이벤트만 제거한 상태에서 워커가 종료됐다고 가정한다. 두 번째 이벤트는 이미 DB에 반영됐지만 처리 목록에 남아 있다.

```text
LREM lab:likes:processing 1 '{"event_id":"e-1","post_id":42,"user_id":101}'
LRANGE lab:likes:processing 0 -1
```

단일 워커가 종료된 것을 확인한 뒤, 두 번째 이벤트를 대기 목록으로 돌리고 다시 가져온다.

```text
LMOVE lab:likes:processing lab:likes:ready LEFT LEFT
LMOVE lab:likes:ready lab:likes:processing LEFT RIGHT
```

앞 절의 SQL에서 `VALUES`를 `(42, 102)` 한 건으로 바꿔 실행한다. 좋아요 수는 그대로 `2`다. 재처리 커밋이 완료되면 이벤트를 제거한다.

```text
LREM lab:likes:processing 1 '{"event_id":"e-2","post_id":42,"user_id":102}'
LLEN lab:likes:processing
```

처리 목록 길이가 `0`이면 실습이 끝난다. 운영에서는 대기 건수와 가장 오래된 이벤트의 대기 시간으로 배치 지연을 확인한다. Redis 자체가 재시작되면 큐의 복구 범위는 RDB와 AOF 등 영속화 설정에 따라 달라진다.

**공식 문서** [LREM](https://redis.io/docs/latest/commands/lrem/) · [Redis 영속화](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
