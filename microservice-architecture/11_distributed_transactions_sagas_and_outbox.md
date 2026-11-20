# Distributed Transactions, Sagas, and Outbox

주문 확정과 재고·결제 처리가 여러 서비스에 걸치면 기술적 트랜잭션과 업무의 완료를 구분해야 한다. 한 DB 안의 불변식은 로컬 트랜잭션으로 보호한다. 여러 저장소가 참여하는 원자적 커밋은 지원 범위·지연·장애 복구 특성을 평가하고, 독립 로컬 커밋을 연결할 때는 Saga의 중간 상태와 보상을 설계한다. [Garcia-Molina와 Salem · Sagas](https://www.cs.princeton.edu/techreports/1987/070.pdf) · [Microservice Saga](https://microservices.io/patterns/data/saga.html)

## 주문 Saga의 성공과 보상

| 단계 | 정상 처리 | 실패하거나 응답을 잃었을 때 |
| --- | --- | --- |
| 주문 접수 | 주문을 `PENDING`으로 저장한다. | 동일 요청 키로 기존 주문을 찾을 수 있게 한다. |
| 재고 예약 | 재고가 가용량을 확인해 예약한다. | 확정된 거절이면 주문을 취소 경로로 보낸다. |
| 결제 승인 | 결제 서비스가 거래 키로 승인한다. | 거절이 확인되면 재고를 해제한다. 타임아웃이면 거래 키로 승인 상태를 조회한다. |
| 주문 확정 | 성공한 예약·승인으로 `CONFIRMED`가 된다. | 앞 단계가 성공한 뒤 확정 불가가 확정되면 결제 취소·재고 해제를 조율한다. |

보상은 이미 커밋된 효과를 업무적으로 되돌리는 새 트랜잭션이다. 발송처럼 되돌리기 어려운 작업이 어느 단계인지 먼저 찾는다. 보상도 실패할 수 있으므로 진행 상태를 기록하고, 중복 호출을 받아도 결과가 일관되게 하며, 자동으로 회복하지 못하면 운영 확인으로 넘긴다.

오케스트레이션은 조정자가 단계·기한·보상을 명시한다. 코레오그래피는 각 참여자가 정해진 이벤트에 반응한다. 참여자가 늘어날수록 흐름을 추적할 방법과 서로의 실패를 해석하는 규칙을 함께 마련한다. [Saga 흐름과 보상](../architecture-pattern/04_saga_pattern.md)

## Dual Write, Outbox, CDC

업무 DB를 커밋한 뒤 별도로 발행하면 두 작업 사이에서 중단될 수 있다. 상태 변경과 발행할 메시지를 같은 DB 트랜잭션으로 기록하고, 릴레이가 Outbox를 폴링하거나 CDC로 커밋된 변경을 읽어 발행한다. 릴레이가 발행한 직후 중단되면 중복 발행될 수 있어 소비자도 멱등해야 한다. Outbox는 한 서비스의 기록과 발행을 연결하며 서비스 간 보상 자체는 Saga의 계약으로 다룬다. [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html) · [Outbox 신뢰성 설계](../engineering-design-training/06_publishing_events_reliably_with_the_transactional_outbox_pattern.md)

분산 데이터베이스를 쓰면 제품이 제공하는 범위에서 여러 파티션에 대한 원자적 트랜잭션을 사용할 수 있다. 여러 서비스의 독립 저장소와 외부 결제 호출까지 같은 커밋이 되는지는 별개로 확인한다. [Google Spanner · Transactions](https://cloud.google.com/spanner/docs/transactions)
