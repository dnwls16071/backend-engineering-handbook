# Database Performance and Query Execution Architecture

쿼리 응답 시간에는 연결 대기, SQL 처리, 잠금 대기, 데이터와 인덱스 페이지 읽기, 결과 전송 등이 포함된다. 요청 지연을 조사할 때는 같은 구간의 처리량과 p95 응답 시간을 함께 기록하고, 애플리케이션에서 보이는 지연과 DB에서 측정한 실행 시간을 대조한다. 평균 응답 시간만 보면 일부 요청에 집중되는 지연을 놓칠 수 있다.

## 1. SQL 실행 계층과 저장 엔진

| 단계 | 하는 일 |
| --- | --- |
| 요청 처리 | 세션과 권한을 확인하고 SQL을 파싱해 참조하는 테이블과 열을 확인한다. |
| 최적화 | 통계와 비용 모델로 테이블 접근 방식, 조인 순서, 정렬 방법 등을 비교한다. |
| 실행 | 계획의 연산자가 행을 읽고, 필터링하고, 조인하거나 집계한다. |
| 저장 엔진 | 테이블과 인덱스 페이지를 읽고, 트랜잭션과 잠금에 따라 행의 읽기와 쓰기를 처리한다. |

MySQL은 SQL 서버와 스토리지 엔진을 구분한다. InnoDB는 테이블과 인덱스를 페이지 단위로 관리하고, 버퍼 풀에 페이지를 캐싱한다. redo 로그는 장애 복구에, undo 레코드는 롤백과 일관된 읽기에 쓰인다. 같은 쿼리라도 페이지가 버퍼 풀에 있는지, 잠금 대기가 있는지에 따라 실제 지연이 달라진다. [MySQL InnoDB Architecture](https://dev.mysql.com/doc/refman/8.4/en/innodb-architecture.html)

## 2. 병목을 확인하는 순서

1. 슬로 쿼리 로그나 Performance Schema에서 실행 빈도와 누적 시간을 확인해 조사 대상을 정한다.
2. 실제 바인딩 값으로 추정 계획을 읽어 스캔, 조인, 정렬 중 작업량이 큰 곳을 찾는다.
3. 실행 계획을 측정해 예상 행 수, 실제 행 수, 반복 횟수를 비교한다.
4. 한 번에 한 가지를 바꾸고 결과가 같은지 비교한다. 측정에 사용한 데이터 분포, 바인딩 값, 캐시 상태도 함께 기록한다.

[Slow Query Log](https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html) · [Performance Schema Statement Digests](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-digests.html)

## 3. 공통 실습 데이터

실습 환경은 MySQL 8.4(InnoDB)다. 빈 실습용 스키마에서 아래 SQL을 한 번 실행하면 고객 1,000명과 주문 10,000건이 생긴다. 이후 문서에서 추가하는 실험용 인덱스는 해당 문서 끝에서 제거한다.

```sql
CREATE TABLE perf5_customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(40) NOT NULL,
    tier VARCHAR(10) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE perf5_orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    status VARCHAR(12) NOT NULL,
    ordered_at DATETIME NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    note VARCHAR(255) NOT NULL
) ENGINE = InnoDB;

INSERT INTO perf5_customers (customer_id, customer_name, tier)
WITH RECURSIVE digit(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM digit WHERE n < 9
),
ids AS (
    SELECT 1 + a.n + 10 * b.n + 100 * c.n AS id
    FROM digit a CROSS JOIN digit b CROSS JOIN digit c
)
SELECT id, CONCAT('Customer ', id), IF(MOD(id, 17) = 0, 'VIP', 'STANDARD')
FROM ids;

INSERT INTO perf5_orders (order_id, customer_id, status, ordered_at, total_amount, note)
WITH RECURSIVE digit(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM digit WHERE n < 9
),
ids AS (
    SELECT 1 + a.n + 10 * b.n + 100 * c.n + 1000 * d.n AS id
    FROM digit a CROSS JOIN digit b CROSS JOIN digit c CROSS JOIN digit d
)
SELECT id,
       1 + MOD(id * 73 + (id DIV 1000) * 11, 1000),
       CASE
           WHEN MOD(id * 7 + (id DIV 100), 37) = 0 THEN 'RETURNED'
           WHEN MOD(id, 4) = 0 THEN 'PENDING'
           ELSE 'PAID'
       END,
       TIMESTAMPADD(MINUTE, id, '2025-01-01 00:00:00'),
       (MOD(id * 137, 50000) + 100) / 100,
       CONCAT('Order ', id)
FROM ids;

ANALYZE TABLE perf5_customers, perf5_orders;
```
