# Solving Cross-Service Workflows with Sagas

Saga는 주문·재고·포인트처럼 소유 저장소가 다른 업무 변경을 로컬 트랜잭션으로 나누고, 중간 실패 때 끝난 변경을 업무 규칙에 따라 보상한다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 어디까지 성공했는지 확인한다

주문 접수를 저장하고 재고 차감에 성공했지만 포인트 잔액 부족이 확정됐다고 하자. 재고 차감과 연결된 보상 식별자로 재고를 복원한 뒤 주문을 취소로 전이한다. 보상이 끝날 때까지 결과는 진행 중으로 노출한다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 실패와 결과 미상을 구분한다

포인트 차감 응답이 시간 초과로 끊겼다면 실제 차감 결과를 모른다. 같은 작업 키로 재시도하거나 참가자 상태를 조회해 결론을 내리고, 이미 차감됐으면 해당 작업과 짝지은 보상도 필요하다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 3. 읽는 순서

[분산 실패](02_understanding_distributed_transaction_failures.md), [구현 핵심](03_modeling_saga_states_and_recovery.md), [2PC](14_understanding_two_phase_commit.md)에서 보장 차이를 확인하고, [TCC 실습](15_understanding_try_confirm_cancel.md), [오케스트레이션 실습](27_defining_an_order_saga.md), [Kafka 코레오그래피 실습](38_designing_event_driven_saga_choreography.md)으로 이어간다. [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Gray·Lamport · Consensus on Transaction Commit](https://arxiv.org/pdf/cs/0408036)
