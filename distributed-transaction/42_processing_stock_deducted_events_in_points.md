# Processing Stock-Deducted Events in Points

포인트 서비스는 StockDeducted를 소비해 포인트를 차감한다. 재고 차감 실패는 포인트 차감을 시작하는 조건이 아니다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 성공과 거절을 이벤트로 표현한다

포인트 잔액·원장·처리 기록을 같은 트랜잭션에 둔다. 잔액이 충분하면 PointsDeducted, 부족하면 PointsRejected를 아웃박스로 기록한다. 포인트 DB의 일시 오류라면 트랜잭션을 종료하고 처리 실패로 남겨 재시도한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [MySQL 8.4 · InnoDB Error Handling](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)

## 2. 거절 이벤트를 원본 재고 차감과 연결한다

PointsRejected에 주문 ID와 원본 재고 작업 ID를 전달해 재고 서비스가 어떤 차감을 복원할지 찾을 수 있게 한다. 늦거나 중복된 이벤트에는 저장된 업무 상태와 멱등 키를 적용한다. [AWS · Saga Choreography](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-choreography.html) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
