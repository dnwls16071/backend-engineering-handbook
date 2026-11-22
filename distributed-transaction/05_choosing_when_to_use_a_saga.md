# Choosing When to Use a Saga

서비스별 변경을 독립적으로 커밋할 수 있고, 업무가 중간 상태와 실패 시 보상을 허용할 때 Saga를 고려한다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 1. 적합한 사례와 비용을 비교한다

| 시나리오 | 판단 기준 | 근거 |
| --- | --- | --- |
| 여러 독립 서비스가 참여하는 주문 | 재고 복원과 포인트 반환을 정의할 수 있다면 해당 분기를 Saga로 표현할 수 있다. | [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) |
| 짧은 단일 저장소 작업 | 한 DB가 요구하는 불변식을 직접 보호한다면 로컬 트랜잭션이 더 작은 설계다. | [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Gray·Lamport · Consensus on Transaction Commit](https://arxiv.org/pdf/cs/0408036) |
| 완료 전 자원이 확실히 확보돼야 하는 예약 | 자원을 먼저 확보하는 TCC 계약과 예약 유지·복구 비용을 비교한다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) |

## 2. 운영자가 실패한 건을 처리할 수 있어야 한다

단계별 타임아웃, 재시도 한도, 해결되지 않은 보상의 조회 방법과 담당자를 함께 설계한다. 롤백에 대응하는 업무 동작이 없으면 해당 단계의 위치나 사용자 승인 절차를 재검토한다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
