# Aggregate Table Design

통계 테이블은 원본에서 계산한 합계나 건수를 일정한 단위로 저장한다. 같은 범위의 원본을 반복해서 읽는 부하를 줄일 수 있다. 먼저 한 행이 나타내는 범위, 어느 시점까지 집계됐는지, 원본이 정정되면 어떻게 다시 계산할지 정한다.

## 1. 집계 단위와 다시 합칠 수 있는 값 정하기

일별 판매 통계는 **업무 날짜 × 판매 채널**을 한 행의 단위로 정할 수 있다. 이 열 조합을 키로 사용하고, 업무 시간대와 날짜 경계, 어떤 상태의 결제를 포함할지 기록한다.

| 집계값 | 일별 행에서 주·월 통계를 구하는 방법 |
| --- | --- |
| 결제 건수와 금액 합계 | 중복되지 않는 날짜 구간의 값을 합한다. |
| 건당 평균 금액 | 일별 금액 합계의 합을 일별 건수의 합으로 나눈다. 건수가 0이면 평균의 표시 규칙을 별도로 정한다. |
| 순구매자 수 | 같은 구매자가 다른 날짜에도 나타날 수 있다. 기간의 원본에서 다시 중복을 제거하거나 별도의 식별 단위로 집계한다. |

금액이 과거에 어떻게 계산됐는지 확인할 수 있도록 결제나 주문 원본을 보존한다. 업무 날짜에는 서비스가 사용하는 시간대를 적용한다. 집계 범위는 시작을 포함하고 끝을 제외하면 일별 경계에서 같은 이벤트를 두 번 읽지 않는다. [MySQL 집계 함수](https://dev.mysql.com/doc/refman/8.4/en/aggregate-functions.html) · [MySQL 날짜와 시간 함수](https://dev.mysql.com/doc/refman/8.4/en/date-and-time-functions.html)

## 2. 같은 날짜를 다시 계산해 덮어쓰기

실습 환경은 MySQL 8.4(InnoDB)다. 빈 스키마의 한 세션에서 위에서부터 실행한다. 실습의 날짜 경계는 UTC다. 등록된 채널별로 한 행씩 만들고, 결제가 없으면 `0`으로 기록한다.

```sql
CREATE TABLE dd18_channels (
    channel_code VARCHAR(20) PRIMARY KEY
) ENGINE = InnoDB;

CREATE TABLE dd18_paid_orders (
    order_id INT PRIMARY KEY,
    channel_code VARCHAR(20) NOT NULL,
    paid_at DATETIME(6) NOT NULL,
    net_amount DECIMAL(12, 2) NOT NULL,
    INDEX idx_dd18_channel_paid (channel_code, paid_at),
    FOREIGN KEY (channel_code) REFERENCES dd18_channels (channel_code)
) ENGINE = InnoDB;

CREATE TABLE dd18_daily_sales (
    report_day DATE NOT NULL,
    channel_code VARCHAR(20) NOT NULL,
    order_count BIGINT NOT NULL,
    net_amount DECIMAL(16, 2) NOT NULL,
    PRIMARY KEY (report_day, channel_code)
) ENGINE = InnoDB;

INSERT INTO dd18_channels VALUES ('store'), ('web');
INSERT INTO dd18_paid_orders VALUES
    (1, 'web', '2026-02-01 00:00:00', 40.00),
    (2, 'web', '2026-02-01 14:00:00', 60.00),
    (3, 'store', '2026-02-01 16:00:00', 25.00),
    (4, 'web', '2026-02-02 00:00:00', 15.00);
```

```sql
INSERT INTO dd18_daily_sales (report_day, channel_code, order_count, net_amount)
SELECT report_day, channel_code, next_count, next_amount
FROM (
    SELECT DATE('2026-02-01') AS report_day,
           c.channel_code,
           COUNT(o.order_id) AS next_count,
           COALESCE(SUM(o.net_amount), 0) AS next_amount
    FROM dd18_channels AS c
    LEFT JOIN dd18_paid_orders AS o
      ON o.channel_code = c.channel_code
     AND o.paid_at >= '2026-02-01 00:00:00'
     AND o.paid_at < '2026-02-02 00:00:00'
    GROUP BY c.channel_code
) AS recomputed
ON DUPLICATE KEY UPDATE
    order_count = recomputed.next_count,
    net_amount = recomputed.next_amount;

SELECT report_day, channel_code, order_count, net_amount
FROM dd18_daily_sales
ORDER BY report_day, channel_code;
```

2월 1일 `store`는 `1건 / 25.00`, `web`은 `2건 / 100.00`이다. 같은 원본 상태에서 두 번째 SQL 블록을 반복해도 결과는 동일하다. 이전 값에 더하는 방식은 재시도할 때 같은 결제를 중복 반영할 수 있다. 채널 목록을 기준으로 집계하므로 등록된 채널의 해당 날짜 원본이 0건이 되더라도 기존 값을 0으로 갱신한다. 집계 단위 자체가 바뀌거나 사라질 수 있다면 대상 범위를 트랜잭션 안에서 통째로 교체하거나 사라진 키를 명시적으로 제거한다. MySQL 예제는 삽입 후보의 값을 파생 테이블의 열로 참조한다. [MySQL INSERT … ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) · [MySQL 트랜잭션 제어](https://dev.mysql.com/doc/refman/8.4/en/commit.html)

## 3. 과거 통계와 최신 원본을 경계에서 합치기

완료된 날짜는 통계 테이블을 읽고, 집계가 완료되지 않은 구간은 원본에서 계산할 수 있다. 통계가 2월 1일까지 끝났다면 두 조회가 같은 경계인 `2026-02-02 00:00:00`을 공유한다.

```sql
SELECT report_day, channel_code, order_count, net_amount
FROM dd18_daily_sales
WHERE report_day >= '2026-02-01'
  AND report_day < '2026-02-02'
UNION ALL
SELECT DATE('2026-02-02'), channel_code, COUNT(*), SUM(net_amount)
FROM dd18_paid_orders
WHERE paid_at >= '2026-02-02 00:00:00'
  AND paid_at < '2026-02-03 00:00:00'
GROUP BY channel_code
ORDER BY report_day, channel_code;
```

앞의 통계 두 행에 2월 2일 `web`의 `1건 / 15.00`이 추가된다. 원본 집계 부담이 크면 마이크로 배치로 고정된 시간 구간을 재계산하고, **어디까지 집계가 완료됐는지** 보여 주는 경계를 결과와 함께 커밋한다. 독자는 그 경계를 기준으로 통계와 아직 반영되지 않은 원본을 겹치지 않게 읽는다. 늦게 도착한 결제나 환불은 이미 끝난 기간을 바꿀 수 있으므로 일정 기간을 다시 계산하거나 영향받은 날짜를 재처리한다. 같은 범위를 동시에 계산할 수 있다면 오래된 원본을 읽은 배치가 더 최신 결과를 덮지 않도록 실행을 직렬화하거나 원본 버전을 비교한다.
