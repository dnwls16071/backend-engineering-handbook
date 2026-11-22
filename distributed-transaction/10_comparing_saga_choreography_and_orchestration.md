# Comparing Saga Choreography and Orchestration

같은 주문 업무에서 다음 단계를 결정하는 위치를 비교한다. 두 방식 모두 로컬 변경, 보상, 중복 요청에 대한 명시적 처리 규칙이 필요하다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 1. 조정 책임과 장애 확인 경로를 비교한다

| 기준 | 코레오그래피 | 오케스트레이션 | 근거 |
| --- | --- | --- | --- |
| 다음 단계의 결정 | 이벤트를 받는 각 참가자 | 상태와 규칙을 보관하는 조정자 | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |
| 장애 조사 | 상관 키로 이벤트·참가자 상태를 연결 | 조정 기록으로 미완료 단계와 참가자를 조회 | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |
| 변경 영향 | 이벤트 계약에 등록된 소비자 검토 | 흐름 정의와 명령·응답 계약 검토 | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) |

## 2. 한 주문 흐름에서 방식을 조합하는 기준

주문의 필수 예약·보상 분기는 오케스트레이터가 관리하고, 주문 완료가 확정된 사실은 알림·검색 소비자가 사용하게 할 수 있다. 하나의 상태를 두 조정 메커니즘이 동시에 소유하지 않도록 완료 이벤트의 발행 시점을 규정한다. [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
