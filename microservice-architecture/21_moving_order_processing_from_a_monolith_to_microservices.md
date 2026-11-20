# Moving Order Processing from a Monolith to Microservices

주문·재고·포인트가 독립 저장소를 소유하게 되면, 주문 서비스의 로컬 트랜잭션은 주문 DB의 변경만 보호한다. 주문을 확정할 조건과 일부 단계만 처리됐을 때의 복구 경로를 서비스 간 계약에 포함한다. [AWS Prescriptive Guidance · Saga Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-patterns.html)

## 1. 분리 전에 모듈의 계약과 소유권 정하기

| 서비스 | 소유하는 상태 | 서비스 간 계약 예시 |
| --- | --- | --- |
| 주문 | 요청 키, 주문 상태, 워크플로 진행 상태 | 주문 접수, 상태 조회 |
| 재고 | 가용 재고, 주문별 차감 또는 예약 | 차감·복원 또는 예약·확정·해제 |
| 포인트 | 잔액, 주문별 원장 기록 | 차감·환급 또는 보류·확정·해제 |

1. 모놀리스 안에서 주문이 재고 및 포인트 내부 테이블에 접근하는 부분을 공개 모듈 인터페이스로 바꾼다.
2. 가용량·잔액 검증과 중복 처리 규칙을 해당 서비스를 소유하는 쪽에 둔다.
3. 인터페이스 구현을 원격 API 또는 메시징 어댑터로 바꿀 때 요청 ID, 거래 ID, 단계 ID, 시간 제한과 오류 의미를 계약에 포함한다.
4. 저장소를 전환할 때 한 데이터의 쓰기 담당자를 정한다. 백필과 일치 여부를 확인한 뒤 쓰기 경로를 전환한다.

## 2. 부분 성공과 결과 미상 다루기

재고는 차감됐고 포인트는 거절됐다면 이미 완료한 재고 단계를 보상한다. 포인트 요청이 타임아웃됐다면 성공 여부가 아직 불명확하다. 같은 단계 ID로 결과를 조회하거나 멱등하게 재호출하고, 확인이 안 되면 주문을 진행 중 상태로 남겨 복구한다.

주문 접수 API는 처리 시간이 긴 경우 `202 Accepted`와 주문 ID를 반환할 수 있다. 상태 조회 API는 `PENDING`, `CONFIRMED`, `COMPENSATING`, `CANCELLED`처럼 클라이언트가 이해할 수 있는 상태를 제공한다. 재시도 중인 단계를 주문 취소와 동일하게 표시하면 사용자가 새 주문을 제출해 실제 중복 효과가 생길 수 있다. [RFC 9110 · 202 Accepted](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted)

## 3. 조정 방식 선택

자원 관리자가 모두 원자적 커밋에 참여할 수 있다면 [Two-Phase Commit and Prepared Transaction Recovery](22_two_phase_commit_and_prepared_transaction_recovery.md)의 복구 비용을 검토한다. 업무 자원을 먼저 확보할 수 있으면 [Try-Confirm-Cancel](23_coordinating_reservations_with_try_confirm_cancel.md)로 예약을 관리한다. 각 서비스에서 업무 변경을 커밋하고 실패 시 보상하는 흐름은 [오케스트레이션](24_orchestrating_order_sagas_and_compensations.md)과 [코레오그래피](25_choreographing_order_sagas_with_kafka.md) 중 조정 책임을 어디에 둘지 결정한다.

관련 문서 [Decomposing Services by Domain Boundaries](05_decomposing_services_by_domain_boundaries.md) · [Distributed Transactions, Sagas, and Outbox](11_distributed_transactions_sagas_and_outbox.md)
