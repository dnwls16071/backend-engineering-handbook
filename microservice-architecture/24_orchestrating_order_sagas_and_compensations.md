# Orchestrating Order Sagas and Compensations

Saga 오케스트레이션에서는 조정자가 어떤 단계를 실행했고, 어떤 단계까지 보상해야 하는지 관리한다. 참가 서비스는 재고 차감·복원, 포인트 차감·환급을 자신의 로컬 트랜잭션으로 실행한다. [AWS Prescriptive Guidance · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 1. 주문 Saga의 단계와 보상

| 단계 | 정상 동작 | 보상이 필요한 경우 |
| --- | --- | --- |
| 주문 생성 | 주문과 Saga를 `PENDING`으로 기록한다. | 이미 접수한 주문은 보상 결과를 반영해 취소한다. |
| 재고 차감 | 주문 ID가 연결된 차감 내역을 기록한다. | 원본 차감 내역을 참조해 재고를 복원한다. |
| 포인트 차감 | 주문 ID를 참조해 포인트 원장에 차감을 추가한다. | 원본 차감 내역을 참조해 환급 내역을 추가한다. |
| 주문 확정 | 재고·포인트 성공이 확인되면 `CONFIRMED`로 전이한다. | 확정 응답이 유실됐으면 주문 상태를 먼저 확인한다. |

포인트 부족이 확정되면 재고 복원을 실행하고 성공을 확인한 뒤 주문을 취소한다. 이미 재고·포인트 차감이 성공했는데 확정할 수 없다고 판단한 경우, 정책에 따라 포인트 환급부터 진행하고 이후 재고를 복원한다. 보상은 최초 변경을 참조하는 새 업무 트랜잭션이다. [AWS Prescriptive Guidance · Saga Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-patterns.html)

## 2. API 클라이언트와 복구 가능한 조정자

주문 API는 접수 결과와 조회 가능한 주문 ID를 반환한다. 조정자의 API 클라이언트는 각 단계에 안정적인 `stepId`를 전달하고, 호출 성공·업무 거절·일시 오류·결과 미상을 구분한다. 참가자는 `stepId`의 실행 내역을 업무 변경과 함께 저장한다.

원격 호출 전 실행할 단계와 ID를 기록하고, 호출 후 결과를 별도로 저장한다. 원격 DB가 커밋한 뒤 조정자가 중단되면 재시작한 작업자가 동일 단계 ID로 재호출하거나 상태를 조회한다. 작업자가 여럿이면 단계 버전이나 임대 등으로 진행 갱신을 조정하고, 참가자의 멱등성으로 중복 요청의 효과를 막는다. 명령을 메시지로 발행한다면 단계 전이와 다음 명령을 로컬 트랜잭션의 Outbox에 같이 기록할 수 있다. [AWS Prescriptive Guidance · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 실패 시 기대 상태

- **포인트 거절**. 재고 복원이 끝나기 전에는 `COMPENSATING`을 유지한다.
- **포인트 응답 유실**. 처리를 보류하고 동일 단계 ID로 결과를 확인한다.
- **재고 복원 응답 유실**. 같은 보상 ID로 재시도해 복원이 한 번만 반영되는지 확인한다.
- **보상 반복 실패**. 완료로 표시하지 않고 남은 단계, 최근 오류와 시도 횟수를 운영자가 확인할 수 있게 한다.

관련 문서 [Distributed Transactions, Sagas, and Outbox](11_distributed_transactions_sagas_and_outbox.md) · [Choreographing Order Sagas with Kafka](25_choreographing_order_sagas_with_kafka.md)
