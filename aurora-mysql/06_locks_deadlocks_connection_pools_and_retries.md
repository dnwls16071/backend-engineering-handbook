# Aurora MySQL Locks, Deadlocks, Connection Pools, and Retries

장기 트랜잭션과 커넥션 풀 대기, 데이터베이스 오류 뒤의 재시도를 같은 시간축에서 확인한다.

## 1. 장기 트랜잭션과 대기 체인 찾기

대기 세션의 PID를 차단 PID에 연결해 연쇄의 첫 원인을 찾는다. 차단 세션은 현재 SQL을 실행하지 않아 `trx_query`가 NULL일 수 있어 트랜잭션 시작과 이전 호출 기록도 본다. 다음 SQL은 같은 인스턴스에서 현재 보이는 행 락 관계와 차단 트랜잭션을 보여 준다. [MySQL sys.innodb_lock_waits](https://dev.mysql.com/doc/refman/8.4/en/sys-innodb-lock-waits.html) · [INNODB_TRX](https://dev.mysql.com/doc/refman/8.4/en/information-schema-innodb-trx-table.html)

```sql
SELECT w.waiting_pid, w.blocking_pid, w.wait_age_secs,
       w.locked_table_schema, w.locked_table_name, w.locked_index,
       b.trx_started AS blocker_started, b.trx_query AS blocker_query
FROM sys.innodb_lock_waits AS w
LEFT JOIN information_schema.innodb_trx AS b
    ON b.trx_id = w.blocking_trx_id
ORDER BY w.wait_age_secs DESC;
```

## 2. 갱신 순서와 반복 데드락 읽기

상품 1과 2를 갱신하는 두 경로가 반대 순서로 행을 잡으면 순환 대기가 생길 수 있다. `SHOW ENGINE INNODB STATUS`의 최근 데드락에서 보유 락과 기다리는 락, 인덱스 이름을 확인한다. 두 경로가 같은 키 순서를 사용하도록 실제 SQL의 접근을 조정한다. 데드락 피해 트랜잭션은 `1213`으로 전체 롤백된다. [InnoDB 데드락](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html) · [데드락 실습](../mysql/51_innodb_deadlock_diagnosis_and_prevention.md)

## 3. 앱 확장과 연결 수 상한 계산하기

앱 인스턴스 수에 인스턴스당 풀 상한을 곱하고 Writer·Reader별로 분리한다. 배치, 관리 연결, 롤링 배포 중 일시적으로 겹치는 앱까지 더한다. 실제 `DatabaseConnections`와 풀 대여 대기, 신규 연결 속도를 함께 본다. 모든 풀의 연결을 동시에 재생성하면 짧은 장애 이후에도 연결 폭주가 이어질 수 있다. [Aurora 연결 지표](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)

## 4. 연결 풀과 RDS Proxy 적용 판단하기

앱 풀의 최대 연결, 유휴 정책, 대여 타임아웃을 먼저 조정한다. 짧은 연결이 많은 환경에서는 RDS Proxy의 백엔드 연결 재사용을 검토한다. 세션 상태로 연결이 고정되면 재사용 효과가 줄 수 있으며, Reader로 보내는 작업에는 읽기 전용 Proxy 엔드포인트를 별도로 설정한다. 프록시와 앱의 양쪽 연결 대기까지 모니터링한다. [RDS Proxy 연결](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-connections.html) · [RDS Proxy 세션 고정](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-pinning.html) · [RDS Proxy 읽기 전용 엔드포인트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-endpoints.html)

## 5. 타임아웃과 재시도 증폭 제한하기

풀 획득, 행 락 대기, 메타데이터 락 대기, 전체 요청의 한도를 구분한다. InnoDB의 행 락 대기 `1205`는 기본적으로 실패 문장을 롤백하고, `1213`은 피해 트랜잭션 전체를 롤백한다. 행 락 타임아웃 후 업무 트랜잭션을 실패로 처리했다면 남은 변경도 롤백한다. 실패 분류와 요청 예산에 맞춰 전체 트랜잭션 재시도를 제한하고 지터를 둔다. 결과를 모르는 결제·주문은 멱등 키의 기존 상태를 확인하고 같은 작업을 다시 시작한다. [InnoDB 오류 처리](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)
