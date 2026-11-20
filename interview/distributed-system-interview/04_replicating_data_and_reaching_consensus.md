# Replicating Data and Reaching Consensus

주문을 받는 서버가 사라졌을 때 어떤 주문이 살아남는지 설명하려면 성공 응답을 보낸 시점, 각 노드가 저장한 로그 위치, 새 쓰기 권한을 가진 노드를 함께 봐야 한다.

## 20. 데이터를 왜 복제하는가?

> 같은 데이터를 여러 노드에 유지하면 한 노드가 멈춰도 복제본으로 서비스를 이어갈 수 있습니다. 읽기 복제본을 쓰면 조회 부하도 분산할 수 있습니다. 장애 전환에서 잃어도 되는 데이터 범위와 읽기에서 허용할 지연을 먼저 정하고 복제 구성을 선택하겠습니다. [PostgreSQL · Log-Shipping Standby Servers](https://www.postgresql.org/docs/18/warm-standby.html) · [MySQL · Replication](https://dev.mysql.com/doc/refman/8.4/en/replication.html)

- **복제 노드를 어디에 배치하나요?** 같은 전원이나 가용 영역에 몰아 두면 공통 장애에 함께 영향을 받습니다. 견뎌야 하는 장애 범위에 맞춰 복제본을 배치하고, 영역 간 왕복 시간이 동기 쓰기에 미치는 영향을 봅니다. [Dynamo §4.6](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html) · [PostgreSQL · Synchronous Replication](https://www.postgresql.org/docs/18/warm-standby.html#SYNCHRONOUS-REPLICATION)
- **운영자가 주문을 실수로 삭제한 경우는요?** 정상적으로 전달된 삭제는 복제본에도 적용됩니다. 삭제 이전 상태가 필요하면 별도로 보관한 백업과 아카이브 로그로 삭제 직전까지 복구합니다. [MySQL · Replication Implementation](https://dev.mysql.com/doc/refman/8.4/en/replication-implementation.html) · [PostgreSQL · Point-in-Time Recovery](https://www.postgresql.org/docs/18/continuous-archiving.html)

## 21. 로그 복제와 동기·비동기 복제는 어떻게 동작하는가?

> 프라이머리가 변경을 로그에 기록하면 복제본이 그 로그를 받아 자기 상태에 적용합니다. 비동기는 복제본의 확인을 기다리지 않고 성공을 응답할 수 있습니다. 동기는 지정한 복제본의 확인을 기다립니다. 제품마다 확인 시점이 다르므로 로그 수신, 디스크 반영, 조회 가능한 상태로 적용 중 어느 단계까지 기다리는지 확인합니다. [PostgreSQL · WAL 설정](https://www.postgresql.org/docs/18/runtime-config-wal.html#GUC-SYNCHRONOUS-COMMIT) · [MySQL · Replication Implementation](https://dev.mysql.com/doc/refman/8.4/en/replication-implementation.html)

| 구성 | 복제 로그와 성공 응답 시점 |
| --- | --- |
| PostgreSQL 물리 스트리밍 복제 | 대기 서버가 WAL을 받아 재생한다. 동기 대기 서버를 구성했을 때 `remote_write`는 원격 파일시스템 쓰기, `on`은 원격 WAL 영속화, `remote_apply`는 영속화와 재생까지 기다린다. [PostgreSQL · WAL 설정](https://www.postgresql.org/docs/18/runtime-config-wal.html#GUC-SYNCHRONOUS-COMMIT) |
| MySQL 비동기·반동기 복제 | 소스의 binlog 이벤트를 복제본의 relay log에 기록하고 적용한다. 반동기는 필요한 수의 복제본에서 relay log를 디스크에 반영했다는 확인을 기다린다. 조회 가능한 시점은 적용 이후이며, 대기 시간 초과 시 소스는 비동기로 전환할 수 있다. [MySQL · Replication Implementation](https://dev.mysql.com/doc/refman/8.4/en/replication-implementation.html) · [MySQL · Semisynchronous Replication](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html) |

- **동기 복제면 어느 복제본에서나 방금 쓴 주문을 읽을 수 있나요?** 읽을 복제본이 해당 주문의 커밋을 적용했는지 확인해야 합니다. PostgreSQL의 `remote_apply`도 확인 응답을 보내는 동기 대기 서버에 대한 보장입니다. 프라이머리에서 읽거나 해당 로그 위치가 재생된 복제본으로 읽기를 보내겠습니다. [PostgreSQL · Synchronous Replication](https://www.postgresql.org/docs/18/warm-standby.html#SYNCHRONOUS-REPLICATION)

## 22. 합의는 무엇이며 Raft는 어떻게 리더를 선출하는가?

> Raft는 여러 노드가 같은 순서로 적용할 로그를 정하는 합의 알고리즘입니다. 팔로워가 일정 시간 유효한 메시지를 받지 못하면 새 임기에서 후보가 됩니다. 전체 투표 노드의 과반수 표를 얻으면 리더가 되고, 리더는 로그를 복제해 커밋한 뒤 상태에 적용합니다. [Raft §5.1–5.3](https://raft.github.io/raft.pdf)

- **후보가 동시에 나오면요?** 선거 대기 시간을 무작위로 정해 동시에 후보가 될 가능성을 낮춥니다. 투표자는 한 임기에 최대 한 후보에게 투표합니다. 표가 나뉘어 과반수를 얻는 후보가 없으면 새 임기에 다시 선거합니다. [Raft §5.2](https://raft.github.io/raft.pdf)
- **로그가 오래된 후보도 과반수 표를 얻을 수 있나요?** 투표자는 마지막 로그 항목의 임기를 먼저 비교하고, 같으면 인덱스를 비교합니다. 후보의 로그가 자신의 로그보다 뒤처지면 투표를 거절합니다. 이 규칙과 커밋 규칙을 함께 써서 커밋된 항목이 이후 리더의 로그에도 포함되게 합니다. [Raft §5.4](https://raft.github.io/raft.pdf)
- **과반수에 복제됐으면 커밋인가요?** 리더는 자기 임기에 만들어진 로그 항목이 자신을 포함한 과반수에 저장됐을 때 그 항목의 커밋을 결정할 수 있습니다. 이전 임기의 항목은 저장된 복제본 수만으로 커밋을 판단할 수 없습니다. 현재 임기 항목이 커밋되면 그 앞의 항목들도 함께 커밋됩니다. [Raft §5.4.2, 그림 8](https://raft.github.io/raft.pdf)
- **노드 5대가 3대와 2대로 끊기면요?** 고정된 투표 노드 5대라면 과반수는 3대입니다. 3대 쪽은 자격을 갖춘 리더를 선출하고 새 로그를 커밋할 수 있습니다. 2대 쪽에 이전 리더가 남아 있어도 새 로그를 커밋할 과반수가 없습니다. [Raft §5.2–5.4](https://raft.github.io/raft.pdf)

## 23. 비동기 복제에서 장애 전환하면 승인된 쓰기도 잃는가?

> 주문 42를 프라이머리에 커밋하고 고객에게 성공을 응답했는데, 그 로그가 대기 서버에 저장되기 전에 프라이머리를 잃었다고 가정하겠습니다. 그 대기 서버를 승격하면 주문 42가 새 프라이머리에 없을 수 있습니다. 데이터 손실 허용 범위에 맞춰 응답 조건을 정하고, 전환할 때는 이전 프라이머리가 다시 쓰는 것도 차단해야 합니다. [PostgreSQL · Log-Shipping Standby Servers](https://www.postgresql.org/docs/18/warm-standby.html) · [MySQL · Semisynchronous Replication](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html)

- **성공 응답은 어떤 상황에서 살아남나요?** 커밋 로그가 어느 노드에 영속화됐는지와 전환에서 어느 노드를 승격하는지에 달려 있습니다. 동기 확인을 받았더라도 그 로그가 없는 노드를 승격하거나 확인한 복제본을 함께 잃으면 손실이 발생할 수 있습니다. 장애 시 허용할 손실 범위인 RPO와 서비스 복구 목표 시간인 RTO를 기준으로 응답 정책과 승격 조건을 정합니다. [PostgreSQL · Synchronous Replication](https://www.postgresql.org/docs/18/warm-standby.html#SYNCHRONOUS-REPLICATION) · [MySQL · Semisynchronous Replication](https://dev.mysql.com/doc/refman/8.4/en/replication-semisync.html)
- **펜싱(fencing)이 왜 필요한가요?** 네트워크가 끊긴 이전 프라이머리가 살아 있을 수 있습니다. 새 프라이머리를 활성화할 때 이전 프라이머리의 쓰기 권한이 사라졌음을 보장해야 합니다. 저장 경로에서 단조 증가하는 권한 토큰을 검증해 이전 토큰의 쓰기를 거절하거나, 이전 서버의 저장소 접근을 차단하는 방법을 씁니다. [PostgreSQL · Failover](https://www.postgresql.org/docs/18/warm-standby-failover.html) · [Chubby §2.4](https://research.google.com/archive/chubby-osdi06.pdf)

## 24. 리더리스 복제의 `N`, `R`, `W`는 무엇인가?

> Dynamo 방식에서는 키마다 고정된 쓰기 리더를 두지 않고 요청을 맡은 코디네이터가 여러 복제본에 요청합니다. `N`은 키의 복제본 수, `R`과 `W`는 각각 읽기와 쓰기 성공에 필요한 응답 수입니다. 동일한 `N`개 중에서 고르면 `R + W > N`일 때 읽기와 성공한 쓰기의 응답 집합이 적어도 한 노드에서 겹칩니다. [Dynamo §4.3–4.6](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)

- **`N=3`, `R=2`, `W=2`면 어떻게 되나요?** A와 B가 쓰기에 응답했다면 이후 읽기에 응답한 두 노드 중 적어도 한 곳은 A나 B입니다. 같은 복제본 집합에서 한 노드가 응답하지 않아도 두 노드가 응답하면 진행할 수 있습니다. `R`이나 `W`를 높이면 더 많은 응답을 기다려야 해서 지연과 실패 가능성이 커질 수 있습니다. [Dynamo §4.5, §6.1](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
- **그럼 항상 최신 값을 읽나요?** 겹침은 같은 복제본 집합을 쓴다는 전제에서 성립합니다. Sloppy quorum으로 쓰기와 읽기가 다른 대체 노드를 이용하면 겹침이 깨질 수 있습니다. 겹치더라도 동시 쓰기, 버전 선택, 일부 노드에만 반영된 쓰기까지 처리하는 규칙이 있어야 선형화 가능성을 논할 수 있습니다. [Dynamo §4.4–4.6](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
- **Raft의 과반수와 어떤 보장이 다른가요?** Raft는 선거와 로그 커밋 규칙을 결합해 어떤 명령이 어떤 순서로 확정됐는지 보장합니다. Dynamo식 응답 수는 개별 읽기·쓰기의 성공 조건이며, 동시 갱신은 여러 버전으로 남아 이후 조정될 수 있습니다. [Raft §5](https://raft.github.io/raft.pdf) · [Dynamo §4.4–4.5](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)

## 25. 복제본의 값이 달라지면 어떻게 수렴시키는가?

> 일시적으로 전달하지 못한 변경은 복구된 노드에 다시 보낼 수 있습니다. 읽기 도중 뒤처진 복제본을 발견하면 보정하고, 조회가 없는 데이터도 백그라운드에서 비교해 맞춥니다. 두 곳에서 같은 키를 동시에 갱신했다면 어느 변경이 다른 변경을 포함하는지 판단하고, 충돌한 버전은 업무에 맞는 규칙으로 합치거나 선택합니다. [Dynamo §4.4, §4.6–4.7, §5](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)

| 기법 | 동작 |
| --- | --- |
| Hinted handoff | 원래 복제본에 쓸 수 없을 때 대체 노드가 변경과 원래 대상 정보를 저장해 두고, 대상이 돌아오면 전달한다. [Dynamo §4.6](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html) |
| Read repair | 읽기에 참여한 복제본이 오래된 버전을 반환하면 코디네이터가 더 최신 버전으로 보정한다. [Dynamo §5](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html) |
| Anti-entropy | 복제본이 백그라운드에서 데이터 차이를 찾아 보정한다. Dynamo는 Merkle tree의 해시가 다른 구간을 좁혀 전송량을 줄인다. [Dynamo §4.7](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html) |

- **버전 충돌은 어떻게 판단하나요?** Dynamo는 벡터 클록으로 한 버전이 다른 버전의 변경을 포함하는지 확인합니다. 두 버전의 변경 이력이 서로를 포함하지 않으면 동시 갱신으로 보고 둘 다 반환할 수 있습니다. 애플리케이션은 내용을 조정해 두 버전을 포함하는 새 버전을 씁니다. [Dynamo §4.4–4.5](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
- **Last Write Wins를 쓰면 어떻게 되나요?** 가장 큰 타임스탬프를 가진 버전을 선택하고 동률 처리 규칙까지 정하면 복제본이 같은 값으로 수렴하기 쉽습니다. 시계 오차로 실제 나중에 발생한 쓰기가 밀릴 수 있고, 선택되지 않은 동시 갱신은 사라질 수 있습니다. 덮어쓰기를 허용하는 주문 메모에는 고려할 수 있습니다. 재고나 결제 상태는 불변식을 지킬 수 있는 조건부 갱신이나 상태 전이 검증이 필요합니다. [Apache Cassandra · Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
