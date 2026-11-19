# Scaling MySQL with Replication, Partitioning, and Sharding

복제는 동일한 데이터의 사본을 운영하고, 파티셔닝은 한 테이블의 행을 여러 구간으로 관리하며, 샤딩은 행을 여러 서버에 나눠 저장한다. 처리량을 높이거나 저장 부담을 줄일 때 어느 작업을 분산하려는지부터 정한다. 실습 환경은 MySQL 8.4(InnoDB)다. [Replication](https://dev.mysql.com/doc/refman/8.4/en/replication.html) · [Partitioning Overview](https://dev.mysql.com/doc/refman/8.4/en/partitioning-overview.html) · [Vitess Sharding](https://vitess.io/docs/reference/features/sharding/)

## 1. 복제와 읽기 트래픽 분산

소스가 바이너리 로그에 변경을 기록하면 레플리카가 이벤트를 받아 적용한다. GTID는 트랜잭션을 고유하게 식별해 복제에서 어떤 트랜잭션이 적용됐는지 추적하는 데 쓰인다. 읽기를 레플리카로 보내면 소스의 부하를 줄일 수 있다. 변경 직후 그 변경을 반드시 읽어야 하는 요청은 소스로 보내거나, 사용하려는 레플리카가 해당 트랜잭션을 적용했는지 확인한다. [Replication with GTIDs](https://dev.mysql.com/doc/refman/8.4/en/replication-gtids.html)

세미싱크 복제는 레플리카의 수신 및 로그 기록 확인을 기다릴 수 있다. 확인 시점과 레플리카가 실제로 변경을 적용하는 시점은 다르다. 복제 지연을 볼 때는 수신과 적용을 구분하고, 장애 조치에서는 어떤 트랜잭션까지 반영된 인스턴스를 승격하는지 확인한다. [Semisynchronous Replication](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html)

## 2. 파티션 프루닝과 샤드 키

| 방식 | 설계에서 확인할 조건 |
| --- | --- |
| 시간 기준 파티셔닝 | 조회 조건에 기간이 있고, 오래된 데이터를 기간 단위로 정리하는지 본다. 프루닝 여부는 실행 계획이 읽는 파티션으로 확인한다. |
| 수평 샤딩 | 고객이나 테넌트처럼 자주 함께 쓰고 읽는 단위를 같은 샤드에 배치한다. 부하 편중, 샤드 간 조인과 트랜잭션, 재분배 시 라우팅을 설계한다. |

MySQL 분할 테이블의 모든 유일 키에는 파티션 식의 열이 포함되어야 한다. 아래 기본 키는 `(event_date, event_id)` 조합의 유일성을 보장한다. `event_id` 단독의 전역 유일성이 업무 규칙이면 모델에서 별도로 해결해야 한다. [Partitioning Keys and Unique Keys](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-partitioning-keys-unique-keys.html) · [Partition Pruning](https://dev.mysql.com/doc/refman/8.4/en/partitioning-pruning.html)

```sql
CREATE TABLE mysql_lab_event_archive (
    event_date DATE NOT NULL,
    event_id BIGINT NOT NULL,
    event_type VARCHAR(16) NOT NULL,
    PRIMARY KEY (event_date, event_id)
) ENGINE = InnoDB
PARTITION BY RANGE COLUMNS (event_date) (
    PARTITION p202501 VALUES LESS THAN ('2025-02-01'),
    PARTITION p202502 VALUES LESS THAN ('2025-03-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);

INSERT INTO mysql_lab_event_archive VALUES
    ('2025-01-15', 1, 'CREATED'),
    ('2025-02-15', 2, 'CREATED');

EXPLAIN FORMAT=TRADITIONAL
SELECT event_id
FROM mysql_lab_event_archive
WHERE event_date >= '2025-02-01' AND event_date < '2025-03-01';
```

`partitions` 열에서 2월 파티션을 읽는지 확인한다. 예제의 첫 파티션은 상한보다 이전인 날짜도 받는다. 실제 월별 보존 정책에서는 가장 이른 파티션의 범위도 확인한다. [RANGE COLUMNS Partitioning](https://dev.mysql.com/doc/refman/8.4/en/partitioning-columns-range.html)

## 3. 압축과 아카이빙

압축은 저장 용량과 I/O를 줄일 수 있고 압축·해제에 CPU를 사용한다. 실제 읽기·쓰기 부하에서 용량, 처리량, 지연을 비교한다. 아카이빙은 자주 쓰지 않는 데이터를 별도 저장소로 옮기는 수명 주기 정책이다. 원본을 정리하기 전에 이관한 구간과 행 수를 검증하고, 필요한 기간의 데이터를 복원하거나 조회하는 경로를 시험한다. [InnoDB Table and Page Compression](https://dev.mysql.com/doc/refman/8.4/en/innodb-compression.html) · [Maintenance of Partitions](https://dev.mysql.com/doc/refman/8.4/en/partitioning-maintenance.html)
