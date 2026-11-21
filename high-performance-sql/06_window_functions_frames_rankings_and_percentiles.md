# Window Functions, Frames, Rankings, and Percentiles

윈도우 함수는 개별 행을 유지하면서 같은 그룹의 다른 행을 참조한다. PostgreSQL 18에서 `PARTITION BY`는 계산 그룹을 나누고, `OVER` 안의 `ORDER BY`는 그룹 안에서 계산에 쓸 순서를 정한다. 결과를 표시할 순서는 쿼리 맨 끝의 `ORDER BY`로 정한다. [PostgreSQL 18 윈도우 함수 튜토리얼](https://www.postgresql.org/docs/18/tutorial-window.html)

## 1. 계좌별 파티션과 프레임으로 누적 잔액 계산하기

같은 세션에서 거래 예제를 실행한다. `delta`는 입금에 양수, 출금에 음수를 쓰는 거래액이다. 계좌의 시작 잔액은 `0`으로 가정한다.

```sql
CREATE TEMP TABLE account_activity (account_id integer NOT NULL, entry_id integer PRIMARY KEY,
    booked_at timestamp NOT NULL, delta integer NOT NULL);
INSERT INTO account_activity VALUES
    (1, 101, '2026-01-01 09:00', 100), (1, 102, '2026-01-01 09:00', -30),
    (1, 103, '2026-01-01 10:00', -40), (1, 104, '2026-01-01 10:15', 20),
    (1, 105, '2026-01-01 10:30', -50), (1, 106, '2026-01-01 11:00', 20),
    (2, 201, '2026-01-01 10:00', 40);

SELECT account_id, entry_id, delta,
       SUM(delta) OVER (
           PARTITION BY account_id ORDER BY booked_at
           RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS balance_by_time,
       SUM(delta) OVER (
           PARTITION BY account_id ORDER BY booked_at, entry_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_balance,
       MAX(delta) OVER (PARTITION BY account_id) AS max_delta
FROM account_activity
ORDER BY account_id, booked_at, entry_id;
```

프레임은 현재 행을 계산할 때 참조할 파티션 내 범위다. 윈도우에 `ORDER BY`를 주고 프레임을 생략하면 기본 `RANGE`는 현재 행과 정렬 키 값이 같은 행까지 모두 포함한다. `ROWS`는 정렬된 행을 한 건씩 센다. 위 예제에서 같은 시각의 `101`과 `102`는 시각별 잔액이 둘 다 `70`이다. 거래별 잔액은 `entry_id`로 순서를 확정하므로 `100`, `70`이다. 최근 거래 3건은 `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`, 최근 1시간의 거래는 시각을 기준으로 `RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW`로 묶을 수 있다.

`MAX(delta) OVER (PARTITION BY account_id)`는 정렬이 없어 계좌 전체에서 최댓값을 구한다. 정렬이 필요한 윈도우에서도 `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`을 지정하면 전체 파티션이 프레임에 포함된다. `MAX`에 기본 `RANGE`를 쓰면 현재 시각까지의 최댓값이 된다. [PostgreSQL 18 윈도우 프레임 문법](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)

## 2. 순번, 공동 순위, 앞뒤 행, 첫·마지막 값 구하기

```sql
SELECT account_id, entry_id, delta,
       ROW_NUMBER() OVER tx AS entry_number,
       RANK() OVER (PARTITION BY account_id ORDER BY delta DESC) AS amount_rank,
       LAG(delta) OVER tx AS previous_delta,
       LEAD(delta) OVER tx AS next_delta,
       FIRST_VALUE(delta) OVER tx AS first_delta,
       LAST_VALUE(delta) OVER tx AS last_in_default_frame,
       LAST_VALUE(delta) OVER (
           tx ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
       ) AS last_delta
FROM account_activity
WINDOW tx AS (PARTITION BY account_id ORDER BY booked_at, entry_id)
ORDER BY account_id, booked_at, entry_id;
```

- `ROW_NUMBER`는 행마다 고유한 순번을 매긴다. 계좌별 최근 두 건을 구하려면 윈도우에서 거래 순서를 내림차순으로 바꾸고, 바깥 쿼리에서 순번이 `2` 이하인 행을 고른다.
- `RANK`는 정렬 값이 같으면 공동 순위를 주고 다음 순위를 건너뛴다. 계좌 `1`에서 `20`인 두 거래는 공동 2위이며, `-30`인 거래는 4위다. 윈도우의 `ORDER BY`는 동점 판정에 필요한 `delta`만 사용한다.
- `LAG`와 `LEAD`는 정렬 순서상 앞·뒤 행을 각각 읽는다. 예제처럼 거리와 기본값을 생략하면 한 행 떨어진 값을 읽고, 범위를 벗어날 때 `NULL`을 반환한다.
- `FIRST_VALUE`와 `LAST_VALUE`는 프레임 양 끝의 값을 읽는다. 위 기본 프레임의 마지막은 거래 순서가 유일하므로 현재 행이다. 전체 프레임을 지정한 `last_delta`는 계좌 `1`의 모든 행에서 `20`이다. [PostgreSQL 18 윈도우 함수](https://www.postgresql.org/docs/18/functions-window.html)

## 3. 백분위수, 누적 분포, 분위 그룹 계산하기

`PERCENTILE_CONT`는 정렬된 입력 사이를 보간하고, `PERCENTILE_DISC`는 누적 비율이 지정한 비율 이상인 첫 관측값을 반환한다. 두 함수 모두 정렬 입력의 `NULL`을 제외한다. PostgreSQL 18에서는 `WITHIN GROUP`을 쓰는 순서 집합 집계 함수이므로, 계좌별로 집계한 뒤 개별 거래 행에 조인한다. 계좌 `1`의 중앙값은 연속 방식 `-5`, 이산 방식 `-30`이다. [PostgreSQL 18 집계 함수](https://www.postgresql.org/docs/18/functions-aggregate.html#FUNCTIONS-ORDEREDSET-TABLE) · [PostgreSQL 18 윈도우에서 사용할 수 있는 집계](https://www.postgresql.org/docs/18/functions-window.html)

```sql
WITH percentiles AS (
    SELECT account_id,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delta) AS median_cont,
           PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY delta) AS median_disc
    FROM account_activity
    GROUP BY account_id
)
SELECT a.account_id, a.entry_id, a.delta, p.median_cont, p.median_disc,
       CUME_DIST() OVER (PARTITION BY a.account_id ORDER BY a.delta) AS cumulative_share,
       NTILE(4) OVER (PARTITION BY a.account_id ORDER BY a.delta, a.entry_id) AS quartile_group
FROM account_activity AS a
JOIN percentiles AS p ON p.account_id = a.account_id
ORDER BY a.account_id, a.delta, a.entry_id;
```

오름차순 `CUME_DIST()`는 현재 값 이하인 행의 비율을 반환해 동점 행을 같은 누적 비율에 둔다. `NTILE(4)`는 정렬된 행을 개수가 비슷한 최대 네 버킷으로 나눈다. 계좌에 거래가 한 건이면 첫 버킷만 생긴다. 동점 행도 다른 버킷으로 갈 수 있으므로 행별 할당을 재현할 수 있도록 `entry_id`를 보조 정렬 키로 추가했다. [PostgreSQL 18 윈도우 함수](https://www.postgresql.org/docs/18/functions-window.html)
