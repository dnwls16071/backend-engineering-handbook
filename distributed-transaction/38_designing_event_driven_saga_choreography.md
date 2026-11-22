# Designing Event-Driven Saga Choreography

코레오그래피에서는 주문·재고·포인트 서비스가 서로의 결과 이벤트에 반응한다. 참가자별로 소비하는 이벤트, 로컬 변경, 다음 이벤트를 정의한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 이벤트 흐름의 소유자를 정한다

| 사실 | 구독 서비스와 다음 행동 | 근거 |
| --- | --- | --- |
| OrderRequested | 재고 서비스가 차감하고 StockDeducted 또는 StockRejected를 발행한다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| StockDeducted | 포인트 서비스가 차감하고 PointsDeducted 또는 PointsRejected를 발행한다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| PointsRejected | 재고 서비스가 앞선 차감을 복원하고 StockRestored를 발행한다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) |
| StockRejected, StockRestored, PointsDeducted | 주문 서비스가 각 결과에 따라 주문을 취소하거나 확정한다. | [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) |

## 2. 완료 단계의 가정을 명시한다

이 예에서 포인트 성공 후 주문 확정은 추가 업무 거절이 없는 로컬 업데이트다. 일시 실패는 이벤트를 재처리한다. 포인트 성공 뒤에도 영구 거절이 가능하다면 포인트 반환과 재고 복원까지 포함하는 실패 흐름을 추가한다. [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
