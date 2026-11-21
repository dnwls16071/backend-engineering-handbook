# MySQL Table Partitioning and Pruning

테이블 파티셔닝은 하나의 논리 테이블을 규칙에 따라 여러 저장 단위로 나눈다. 기간별로 조회하고 보관이 끝난 데이터를 월 단위로 제거하는 이벤트 테이블에 유용하다. 쿼리에서 파티션 키의 범위를 알 수 있으면 옵티마이저가 대상 밖의 파티션을 건너뛰는 프루닝을 할 수 있다. [MySQL 파티셔닝 개요](https://dev.mysql.com/doc/refman/8.4/en/partitioning-overview.html) · [MySQL 파티션 프루닝](https://dev.mysql.com/doc/refman/8.4/en/partitioning-pruning.html)

## 날짜 경계와 실행 계획

```sql
CREATE TABLE event_log_example (
    event_date DATE NOT NULL,
    event_id BIGINT NOT NULL,
    tenant_id BIGINT NOT NULL,
    PRIMARY KEY (event_date, event_id),
    KEY ix_event_tenant_date (tenant_id, event_date)
) ENGINE = InnoDB
PARTITION BY RANGE COLUMNS (event_date) (
    PARTITION p_before_nov VALUES LESS THAN ('2026-11-01'),
    PARTITION p_202611 VALUES LESS THAN ('2026-12-01'),
    PARTITION p_202612 VALUES LESS THAN ('2027-01-01'),
    PARTITION p_future VALUES LESS THAN (MAXVALUE)
);

EXPLAIN FORMAT=TRADITIONAL
SELECT event_date, event_id
FROM event_log_example
WHERE tenant_id = 42
  AND event_date >= '2026-11-01'
  AND event_date < '2026-12-01';
```

예제에서는 계획의 `partitions`에 `p_202611`이 선택되는지 본다. 그 파티션 안에서 접근하는 행은 인덱스 설계에 따라 달라진다. 날짜 조건 없이 이벤트 ID만 찾으면 여러 파티션을 확인할 수 있다. [RANGE COLUMNS 파티셔닝](https://dev.mysql.com/doc/refman/8.4/en/partitioning-columns-range.html) · [MySQL EXPLAIN 출력](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html)

## 제약과 보관 운영

- MySQL에서는 기본 키를 포함한 모든 유일 키에 파티셔닝 표현식이 사용하는 열이 있어야 한다. 예제의 `(event_date, event_id)`는 두 열의 조합을 유일하게 만든다. 이벤트 ID가 날짜와 무관하게 유일해야 하는 시스템이라면 이 제약을 별도로 설계한다. [파티션 키와 유일 키 제약](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-partitioning-keys-unique-keys.html)
- MySQL 8.4의 사용자 정의 파티셔닝을 적용한 InnoDB 테이블에는 외래 키를 두거나 다른 테이블의 외래 키가 해당 테이블을 참조하게 할 수 없다. 기존 관계를 먼저 확인한다. [파티셔닝과 스토리지 엔진 제약](https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations-storage-engines.html)
- `p_future`의 데이터를 새 월별 파티션으로 옮길 때는 범위 재구성을 검토한다. 파티션을 삭제하면 해당 범위의 데이터도 삭제된다. 작업 전 실제 경계, 보관 기간, 백업과 잠금 영향을 확인한다. [MySQL 파티션 관리](https://dev.mysql.com/doc/refman/8.4/en/partitioning-management-range-list.html) · [Scaling MySQL with Replication, Partitioning, and Sharding](16_scaling_mysql_with_replication_partitioning_and_sharding.md)
