# Consistency Models and Regional Network Partitions

## 26. 프로필 읽기의 일관성 모델

| 모델 | 닉네임을 바꾼 직후의 조회 |
| --- | --- |
| 강한 일관성 (여기서는 선형화 가능성, linearizability) | 쓰기 성공 응답 뒤에 시작된 조회는 어느 사용자가 어느 리전에서 요청해도 그 변경까지 반영된 상태를 읽는다. 조회와 겹쳐 진행된 후속 쓰기는 조회 시작부터 응답까지의 구간 안에서 앞이나 뒤에 놓일 수 있다. [Herlihy와 Wing, *Linearizability*](https://www.cs.columbia.edu/~wing/publications/HerlihyWing90.pdf) |
| 최종 일관성 (eventual consistency) | 복제가 밀린 리전에서는 이전 닉네임을 읽을 수 있다. 새 쓰기가 멈추고 복제와 충돌 처리가 진행되면 복제본들이 같은 값으로 수렴한다. 수렴 시간의 상한을 약속하려면 별도의 보장이 필요하다. [Vogels, *Eventually Consistent*](https://www.allthingsdistributed.com/2008/12/eventually_consistent.html) |
| 자기 쓰기 읽기 (read-your-writes) | 닉네임을 수정한 세션의 후속 읽기에 해당 변경이 반영된다. 다른 세션의 읽기는 그보다 오래된 상태를 볼 수 있다. 다른 기기에서도 같은 보장이 필요하면 세션 상태를 공유해야 한다. [Terry 외, *Session Guarantees*](https://www.cs.cornell.edu/courses/cs734/2000FA/cached%20papers/SessionGuaranteesPDIS_1.html) |

선형화 가능성은 한 연산이 완료된 뒤 다른 연산이 시작됐다면 그 순서를 결과에 반영한다. 직렬 가능성(serializability)은 여러 트랜잭션의 결과가 어떤 순차 실행과 같음을 보장한다. 엄격한 직렬 가능성(strict serializability)은 트랜잭션 간 실제 시간 순서까지 보장한다. 스냅샷 읽기는 정해진 시점의 상태를 보며, 과거 시점의 스냅샷도 읽을 수 있다. [PostgreSQL 트랜잭션 격리](https://www.postgresql.org/docs/18/transaction-iso.html) · [etcd API 보장](https://etcd.io/docs/v3.6/learning/api_guarantees/#strict-serializability)

## 27. 수정한 본인에게는 어떻게 새 값을 바로 보여주는가?

프로필을 수정한 세션의 후속 조회를 쓰기를 처리한 샤드의 현재 주 DB로 보내면 자기 쓰기 읽기를 보장할 수 있다. 세션 정보가 앱 인스턴스 사이에서도 유지되어야 하며, 읽기는 커밋 이후의 새 스냅샷에서 시작한다. 쓰기가 장애 전환 뒤에도 보존된다는 조건을 함께 확인한다. [Terry 외, *Session Guarantees*](https://www.cs.cornell.edu/courses/cs734/2000FA/cached%20papers/SessionGuaranteesPDIS_1.html) · [PostgreSQL · Hot Standby](https://www.postgresql.org/docs/17/hot-standby.html#HOT-STANDBY-USERS)

복제본을 활용하려면 쓰기가 커밋된 뒤 샤드와 복제 이력, 커밋 위치를 식별하는 토큰을 반환한다. 후속 읽기를 처리할 복제본이 해당 샤드의 동일한 복제 이력에서 토큰 위치까지 빠짐없이 적용했다면 그 복제본에서 읽을 수 있다. 도쿄가 `41`까지 적용했다면 `41`을 쓴 세션의 읽기를 처리할 수 있다. 서울에서 다른 사용자의 `42`가 이미 완료됐는지는 이 토큰만으로 알 수 없다. [Terry 외, *Session Guarantees*](https://www.cs.cornell.edu/courses/cs734/2000FA/cached%20papers/SessionGuaranteesPDIS_1.html) · [Azure Cosmos DB 세션 토큰](https://learn.microsoft.com/azure/cosmos-db/consistency-levels#session-consistency)

## 28. 서울의 쓰기 성공 직후 도쿄가 고립되면

| 시각 | 프로필 샤드에서 일어난 일 |
| --- | --- |
| 12:00:00.100 | 서울 리더가 새 닉네임을 로그 위치 `41`에 기록한다. 서울과 제3 리전의 복제로 쓰기가 커밋되고, 서울이 클라이언트에 성공을 반환한다. 도쿄는 `40`까지만 적용한 상태다. |
| 12:00:00.110 | 도쿄가 서울 및 제3 리전과 통신할 수 없게 된다. 서울과 제3 리전은 계속 서로 통신한다. |
| 12:00:00.120 | 도쿄에서 프로필 조회가 시작된다. 선형화 가능한 조회라면 `41` 또는 이후 상태를 읽어야 한다. 화면이 최종 일관성을 허용하면 이전 닉네임으로 응답할 수 있다. |

쓰기 성공 응답(ACK)의 기준을 먼저 확인한다. 요청 접수, 서울 내 영속화, 합의 프로토콜에 따른 커밋은 각각 다른 시점이다. 예시의 ACK는 커밋된 쓰기의 성공을 뜻한다. 도쿄의 상태 머신에는 해당 로그가 늦게 적용될 수 있다. 서울에만 저장한 상태에서 성공을 반환하는 설계라면 이후 서울을 잃었을 때 그 쓰기가 새 리더에 남을지도 따로 확인해야 한다. [Raft 논문 §5.3, §8](https://raft.github.io/raft.pdf) · [복제와 합의](04_replicating_data_and_reaching_consensus.md)

## 29. 최신 값이 필수라면 도쿄는 어떻게 응답하는가?

1. **권한이 확인된 읽기 경로를 찾는다.** 현재 리더의 선형화 가능한 읽기로 전달하거나, 저장소의 정족수 기반 읽기 절차를 사용한다. Raft의 `ReadIndex`를 사용하는 경우, 프로토콜이 해당 요청에 유효한 읽기 기준 인덱스를 확인한 뒤 그 위치까지 적용한 복제본에서 로컬로 읽을 수 있다. 리더 임대(lease)를 쓰는 구현은 다른 리더가 그 기간에 쓰기를 커밋할 수 없도록 보장해야 하며, 시계 오차 등 프로토콜의 시간 가정을 만족해야 한다. 예전에 리더였다는 기록과 로컬 TTL만으로는 읽기 권한을 입증할 수 없다. [Raft 논문 §8](https://raft.github.io/raft.pdf) · [etcd Raft `ReadIndex`](https://pkg.go.dev/go.etcd.io/etcd/raft/v3#Node)
2. **요청 기한 안에만 대기한다.** 권한 확인이나 복제본 적용을 짧게 기다린다. 기한까지 필요한 보장을 만족할 수 없으면 일시적으로 조회할 수 없음을 알린다. HTTP API는 `503 Service Unavailable`을 반환하고, 재시도까지의 시간을 안내할 수 있으면 `Retry-After`를 붙일 수 있다. [RFC 9110 §15.6.4](https://www.rfc-editor.org/rfc/rfc9110.html#name-503-service-unavailable)

### CAP에서 보장 범위를 설명하기

- **C** (Consistency)는 읽기와 쓰기가 선형화 가능하다는 보장이다. 앞서 완료된 쓰기가 뒤에 시작된 읽기에 반영된다. [Gilbert와 Lynch, CAP 논문 §2.1](https://cs.nyu.edu/~apanda/classes/sp25/papers/gilbert02brewers.pdf)
- **A** (Availability)는 고장 나지 않은 노드가 받은 모든 요청에서 해당 연산의 유효한 결과를 결국 반환한다는 보장이다. 응답 시간 상한은 정의에 포함되지 않는다. `503`으로 읽기를 거절하거나 단절이 끝날 때까지 무기한 대기하면 이 보장을 충족할 수 없다. [Gilbert와 Lynch, CAP 논문 §2.2–3.1](https://cs.nyu.edu/~apanda/classes/sp25/papers/gilbert02brewers.pdf)
- **P** (Partition tolerance)는 노드 집단 사이의 메시지가 계속 유실될 수 있는 장애 상황을 고려한다는 뜻이다. 서울과 도쿄가 통신할 수 없으면, 도쿄는 서울에서 완료된 쓰기가 있는 경우와 없는 경우를 로컬 상태만으로 구별할 수 없다. 그 조회에서 C를 지키려면 A를 포기해야 할 수 있다. 도쿄의 로컬 상태로 계속 응답하는 정책은 최신성 보장을 완화한다. [Gilbert와 Lynch, CAP 논문 §2.3 및 §3.1](https://cs.nyu.edu/~apanda/classes/sp25/papers/gilbert02brewers.pdf)

단절이 없는 평상시에도 원격 정족수 확인은 왕복 시간만큼 읽기 비용을 높일 수 있다. 로컬 복제본을 읽을 때의 지연과 최신성은 평상시에도 따져야 하고, CAP의 질문은 리전 간 통신이 끊겼을 때 어느 연산을 계속 제공할 수 있는지에 관한 것이다. 이 선택은 [게시글 생성·조회 서비스 설계](06_designing_a_post_creation_and_read_service.md)에서도 조회 경로별로 적용된다. [etcd API 보장](https://etcd.io/docs/v3.6/learning/api_guarantees/#linearizability)

## 30~60초 면접 답변

**프로필에는 어떤 일관성 모델을 선택하겠습니까?**

> 프로필 편집 화면에서는 저장한 본인이 바로 새 닉네임을 봐야 하므로 자기 쓰기 읽기를 보장하겠습니다. 쓰기가 커밋되면 받은 토큰을 후속 조회에 보내고, 해당 샤드에서 그 위치까지 적용한 복제본만 사용합니다. 다른 사람이 보는 공개 프로필은 잠시 이전 닉네임을 보여도 된다면 최종 일관성으로 로컬에서 읽겠습니다. 누구든 쓰기 성공 이후 시작한 조회에서 변경을 봐야 한다면 그 조회에 선형화 가능성을 요구하겠습니다.

**서울이 쓰기 성공을 반환한 뒤 도쿄가 고립됐고, 도쿄 조회에도 최신 값이 필요하면 어떻게 하겠습니까?**

> 성공 응답이 커밋을 뜻한다고 가정하겠습니다. 서울에서 `41`이 완료됐고 도쿄가 `40`까지만 적용했다면 도쿄의 로컬 값으로는 응답할 수 없습니다. 먼저 권한이 확인된 리더나 정족수에 접근해 읽기 기준을 얻을 수 있는지 확인하겠습니다. 기준까지 적용한 복제본이 있으면 거기서 읽고, 요청 기한까지 확인할 수 없다면 `503`을 반환하겠습니다. 도쿄의 해당 조회를 일시적으로 제한해 선형화 가능성을 지키는 선택입니다.
