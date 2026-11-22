# Evaluating Choreography Trade-Offs

코레오그래피에서 각 참가자는 필요한 이벤트에 독립적으로 반응한다. 전체 흐름이 여러 구독과 이벤트 계약에 분산되므로 운영 시각에서 경로를 복원할 수 있어야 한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 단순한 이벤트 관계에서 얻는 이점

기존 이벤트에 독립 조회 모델이나 알림 소비자를 추가하는 경우, 발행 서비스에 새 호출 순서를 넣을 필요가 줄어든다. 같은 이벤트가 예약과 같은 필수 단계를 시작하는지, 알림 같은 부수 효과만 만드는지는 계약에서 구별한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 2. 흐름 추적이 어려워지는 지점을 찾는다

이벤트 그래프에 순환이나 여러 종료 분기가 생기면 서비스별 조각만으로 전체 진행 상태를 복원하기 어렵다. 이벤트 버전, 소유자, 기간별 미완료 Saga 수, 보상 진행 상황을 기록한다. 조정이 필요한 분기가 많다면 명시적 조정 모델을 비교한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
