# Comparing Sagas with Local ACID Transactions

비교 단위는 로컬 DB 트랜잭션과 여러 서비스에 걸친 Saga 전체다. Saga의 각 단계에는 로컬 ACID 트랜잭션을 사용할 수 있다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 업무 전체와 한 DB에서의 보장을 비교한다

| 속성 | 로컬 DB 범위 | Saga 업무 범위 | 근거 |
| --- | --- | --- | --- |
| 원자성 | 한 트랜잭션의 로컬 변경을 커밋하거나 롤백한다. | 나뉜 단계의 커밋을 완료하거나 이미 완료한 변경을 보상한다. | [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) |
| 일관성 | 해당 DB와 업무 코드가 걸어 둔 제약을 검사한다. | 서비스 간 제약은 예약·전이·대사로 관리한다. | [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) |
| 격리성 | DB의 격리 수준과 읽기 방식에 따른다. | 중간 결과를 다른 요청이 관찰할 수 있어 업무 격리가 필요하다. | [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) |
| 지속성 | 커밋한 변경은 DB의 지속성 보장에 따른다. | 단계 결과와 재개에 필요한 진행 기록을 내구성 있게 저장한다. | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Gray·Lamport · Consensus on Transaction Commit](https://arxiv.org/pdf/cs/0408036) |

## 2. 사용자가 보는 결과를 명시한다

주문 요청을 접수한 응답과 주문 자체가 확정된 응답을 구분한다. 진행 중과 보상 중 상태를 제공하고, 서비스 간 불변식은 중간 상태와 완료 상태를 별도로 검증한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)
