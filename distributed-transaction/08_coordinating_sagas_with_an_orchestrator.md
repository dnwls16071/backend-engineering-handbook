# Coordinating Sagas with an Orchestrator

오케스트레이터는 업무 단계의 순서, 다음 명령, 보상 분기를 관리하고 실제 재고·포인트 변경은 각 참가자가 로컬에서 수행한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 명령과 결과를 단계별로 저장한다

재고 차감 결과가 성공이면 포인트 차감 명령을 예약한다. 명시적 포인트 거절을 받으면 기록된 재고 차감에 연결된 복원 명령을 보낸다. 단계별 요청 키와 결과를 저장해 작업자가 재시작해도 같은 단계를 재개할 수 있다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 실행 전후의 장애를 처리한다

명령 전송 뒤 응답을 못 받은 경우는 결과 미상으로 남긴다. 다음 명령으로 넘어가기 전에 자신이 기록한 현재 단계와 참가자의 결과를 대조한다. 비동기 발행이면 상태 전이와 발행 의도를 아웃박스에 함께 넣는다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
