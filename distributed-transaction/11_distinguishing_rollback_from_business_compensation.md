# Distinguishing Rollback from Business Compensation

로컬 롤백은 아직 커밋하지 않은 변경을 취소한다. Saga 보상은 먼저 커밋된 변경의 업무 효과를 상쇄하도록 새 변경을 커밋한다. [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) · [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [Microsoft · Saga](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)

## 1. 이전 값 복원과 업무 효과 상쇄를 구별한다

재고 차감 후 다른 주문이 재고를 썼으면, 당시의 전체 재고 값을 덮어쓰는 대신 원본 차감량만큼 복원한다. 포인트 반환은 원본 차감 원장 행을 지우지 않고 해당 작업을 참조하는 반환 행을 추가하는 방식으로 추적할 수 있다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [García-Molina·Salem · Sagas](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf)

## 2. 보상이 끝날 때까지 진행 상태를 남긴다

보상 명령에도 멱등 키와 재시도 정책을 준다. 보상 순서는 변경 간 의존관계에 맞추며, 처리 한도를 넘으면 중간 성공 기록을 보존하고 사람의 확인에 필요한 주문·단계 정보를 남긴다. [Microsoft · Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
