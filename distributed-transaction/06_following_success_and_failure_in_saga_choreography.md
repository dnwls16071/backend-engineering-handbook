# Following Success and Failure in Saga Choreography

코레오그래피에서는 참가자가 앞 단계의 이벤트를 소비하고, 자신의 로컬 업무 결과를 이벤트로 발행한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 1. 성공과 실패를 주문·재고·포인트에 연결한다

주문 접수 → 재고 차감 완료 → 포인트 차감 완료 → 주문 완료를 성공 경로로 둔다. 포인트 거절은 재고 복원을 시작하는 사실로 처리하고, 복원 완료를 소비한 주문 서비스가 취소를 완료한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)

## 2. 전달 실패와 업무 실패를 구별한다

DB 커밋 뒤 브로커 발행 사이의 간격은 로컬 아웃박스로 복구한다. 이벤트의 중복 수신이나 재전달은 소비자 멱등성으로 처리한다. 재고가 실제로 부족한 경우에는 명시적인 거절 이벤트를 기록한다. [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
