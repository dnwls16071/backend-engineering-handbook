# Resolving Pending TCC Orders

Pending은 접수 이후 진행 중이거나 참가자 결과가 아직 확인되지 않은 상태다. 재처리 워커는 주문의 결정 기록부터 확인한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 1. 같은 결정을 끝까지 적용한다

복구 워커는 오래된 주문을 찾아 결정, 보낸 명령, 참가자 상태를 대조한다. 결정 전이면 상태 조회 또는 취소 정책을 적용한다. 확정·취소 결정이 있으면 누락된 참가 호출만 같은 키로 실행한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 2. 장기 미결의 복구 경로를 운영한다

오래된 예약은 조사 신호로 사용한다. 참가자가 스스로 예약을 풀려면 지연된 Confirm을 안전하게 막는 별도 규칙이 필요하다. 자동 복구가 안 되는 건은 주문 ID, 분기 키, 예약 수량, 최종 시도를 남겨 대사와 수동 복구에 사용한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
