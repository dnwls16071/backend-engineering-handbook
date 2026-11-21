# Aurora PostgreSQL Vacuum, Bloat, and Transaction ID Monitoring

UPDATE 이후 늘어난 파일 크기와 VACUUM이 회수할 수 있는 행 버전을 구분하고, 오래된 스냅샷과 트랜잭션 ID 나이를 추적한다. 아래 SQL은 별도의 PostgreSQL 18 실습 데이터베이스에서 실행한다.

## 1. UPDATE를 반복하면 테이블이 커지는 이유

PostgreSQL은 UPDATE마다 새 행 버전을 만든다. 오래된 버전이나 페이지 여유 공간이 누적되면 행 수가 같아도 파일이 커질 수 있다. 세 번의 UPDATE 뒤 테이블 크기가 네 배가 된 상황은 하나의 관측 사례다. 실제 증가율은 기존 스냅샷, HOT 갱신, 페이지 여유와 정리 진행에 따라 달라진다. 힙 크기와 인덱스·TOAST를 포함한 전체 크기를 따로 읽는다. [PostgreSQL MVCC와 VACUUM](https://www.postgresql.org/docs/18/routine-vacuuming.html) · [힙과 테이블 팽창 실습](../postgresql/09_postgresql_mvcc_vacuum_and_bloat_management.md)

아래 실습은 결과를 관찰하는 동안 테이블 하나의 일반 autovacuum을 끈다. 운영 테이블에서는 이 설정을 사용하지 않는다. 실습이 끝나면 테이블의 옵션을 되돌린다.

```sql
CREATE TABLE aurora_lab_versions (
    id integer PRIMARY KEY,
    revision integer NOT NULL,
    payload text NOT NULL
) WITH (autovacuum_enabled = false);

INSERT INTO aurora_lab_versions
SELECT g, 0, repeat('a', 200) FROM generate_series(1, 1000) AS s(g);

SELECT pg_relation_size('aurora_lab_versions'),
       pg_total_relation_size('aurora_lab_versions');
```

## 2. VACUUM이 제거하지 못한 버전 확인하기

세션 A에서 `BEGIN ISOLATION LEVEL REPEATABLE READ` 후 `SELECT sum(revision) FROM aurora_lab_versions`로 스냅샷을 만든다. 세션 B에서 아래 세 UPDATE를 각각 커밋하고 일반 VACUUM을 실행한다. A가 여전히 이전 버전을 볼 수 있으므로 일부 버전은 아직 제거할 수 없다. `VACUUM VERBOSE`의 제거 불가 행 수와 세션의 `backend_xmin`을 확인한다. 오래된 트랜잭션 외에 준비된 트랜잭션 및 복제 슬롯도 가시성 하한에 영향을 줄 수 있다. [Aurora의 VACUUM 차단 원인](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Appendix.PostgreSQL.CommonDBATasks.Autovacuum_Monitoring.Resolving_Identifiableblockers.html)

```sql
UPDATE aurora_lab_versions SET revision = revision + 1, payload = repeat('b', 200);
UPDATE aurora_lab_versions SET revision = revision + 1, payload = repeat('c', 200);
UPDATE aurora_lab_versions SET revision = revision + 1, payload = repeat('d', 200);

VACUUM (VERBOSE) aurora_lab_versions;
```

## 3. 트랜잭션 종료와 실제 정리 사이의 시간 측정하기

A에서 COMMIT한 시각과 다음 VACUUM이 제거를 보고한 시각은 다를 수 있다. 관측된 3초는 해당 실습의 결과이며 자동 정리의 고정 주기는 아니다. B에서 다시 `VACUUM (VERBOSE) aurora_lab_versions`를 실행해 제거 가능 행이 달라졌는지 확인한다. 운영에서는 `pg_stat_progress_vacuum`과 `last_autovacuum`, `n_dead_tup` 추정치를 함께 본다. 정리가 끝나도 재사용을 위해 파일이 유지될 수 있다. [VACUUM 진행 상태](https://www.postgresql.org/docs/18/progress-reporting.html) · [누적 통계](https://www.postgresql.org/docs/18/monitoring-stats.html)

## 4. VACUUM과 VACUUM FULL의 락·공간 차이

일반 VACUUM은 제거 가능한 튜플의 공간을 테이블 내부에서 다시 쓸 수 있게 한다. 끝부분이 비면 조건에 따라 파일을 줄일 수도 있다. `VACUUM FULL`은 테이블 전체를 다시 쓰고 새 파일을 만든다. 작업 동안 강한 락을 잡고 추가 디스크가 필요하므로 크기 감소만 보고 이벤트 중 실행을 결정하지 않는다. 실습을 마친 뒤 `ALTER TABLE aurora_lab_versions RESET (autovacuum_enabled)`로 설정을 복원한다. [PostgreSQL VACUUM 명령](https://www.postgresql.org/docs/18/sql-vacuum.html)

## 5. 트랜잭션 ID 나이와 동결 상태 감시하기

트랜잭션 ID가 순환하기 때문에 오래된 버전을 동결해 계속 올바르게 보이게 해야 한다. Aurora의 `MaximumUsedTransactionIDs`와 아래 DB·테이블 나이의 추세를 비교하고, 오래된 테이블의 VACUUM이 완료되는지 확인한다. 평균 나이보다 가장 오래된 기준과 증가 속도를 본다. [Aurora autovacuum](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Appendix.PostgreSQL.CommonDBATasks.Autovacuum.html) · [PostgreSQL XID 랩어라운드 방지](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND)

```sql
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
WHERE datallowconn
ORDER BY xid_age DESC;

SELECT c.oid::regclass AS table_name,
       greatest(age(c.relfrozenxid), age(t.relfrozenxid)) AS xid_age
FROM pg_class AS c
LEFT JOIN pg_class AS t ON t.oid = c.reltoastrelid
WHERE c.relkind IN ('r', 'm')
ORDER BY xid_age DESC NULLS LAST
LIMIT 10;
```
