# Evaluating Orchestration Trade-Offs

오케스트레이션은 단계와 실패 분기를 한 곳에서 읽을 수 있게 하지만, 조정 상태와 복구 작업이 추가된다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 중앙 상태가 해결하는 문제를 정한다

여러 참가자의 결과를 모아 하나의 결정을 내려야 할 때 상태 머신이 유용하다. 지연 단계, 시도 횟수, 보상 진행 상태를 같은 주문 ID로 조회하고, 재실행의 사유를 추적할 수 있게 남긴다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 조정 장애가 진행을 멈추는 조건을 설계한다

여러 워커가 같은 Saga를 처리해도 상태 전이의 버전 조건을 검사하고 참가자 명령은 같은 작업 키를 유지한다. 하나의 논리적 조정 상태를 내구성 있게 보관하고, 인스턴스 재시작 시 이전 작업을 다시 맡을 수 있게 한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [MySQL 8.4 · InnoDB Statement Locks](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)
