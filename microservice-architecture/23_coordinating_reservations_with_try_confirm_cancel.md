# Coordinating Reservations with Try-Confirm-Cancel

TCC는 각 서비스가 업무 자원을 먼저 예약한 뒤 조정자의 결정을 받아 확정하거나 해제하는 방식이다. 재고·포인트 서비스는 각 단계의 변경을 자신의 로컬 DB에 커밋한다. [Apache Seata · TCC Mode](https://seata.apache.org/docs/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 1. 상품과 포인트의 TCC 계약

| 단계 | 상품 서비스 | 포인트 서비스 |
| --- | --- | --- |
| Try | 가용 재고를 검사해 주문 수량을 예약하고, 다른 주문이 사용할 수 있는 수량에서 뺀다. | 가용 잔액을 확인해 필요한 포인트를 보류한다. |
| Confirm | 예약된 수량을 확정 차감으로 전환한다. | 보류 금액을 확정 차감하고 원장 내역을 남긴다. |
| Cancel | 예약을 해제하고 가용 재고를 복원한다. | 보류한 금액을 풀어 가용 잔액을 복원한다. |

참가자는 `(transaction_id, branch_id)`로 예약을 식별하고, 단계가 반복돼도 동일한 결과를 반환한다. Try에서 가용량을 확인하고 예약할 때 조건부 갱신이나 행 잠금을 사용한다. 예약 내역과 가용량 변경은 같은 로컬 트랜잭션에 두고, Confirm에서 가용량을 한 번 더 차감하지 않는다.

## 2. 요청 순서 뒤바뀜과 중복 처리

| 도착한 호출 | 허용되는 처리 |
| --- | --- |
| Try가 이미 성공한 뒤 같은 Try | 같은 예약을 반환한다. 요청 내용의 불일치는 충돌로 처리한다. |
| Confirm을 여러 번 수신 | 처음만 확정하고 이후에는 저장된 확정 결과를 반환한다. |
| Try 기록 없이 Cancel을 먼저 수신 | 복원할 자원이 없으므로 취소 표시만 남긴다. |
| Cancel 뒤 지연된 Try | 취소 표시를 보고 예약을 거절한다. |

취소 표시와 예약 상태를 같은 식별자에 대해 일관되게 전이한다. 표시를 너무 일찍 삭제하면 지연 요청이 다시 예약할 수 있다. 세부 상태명과 보존 기간은 메시지 수명과 재시도 기간에 맞춘다. [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 3. 주문 API, Retry와 Pending 해소

주문 서비스는 주문 접수와 각 참가자의 진행을 저장하고, 모든 Try가 성공하면 확정 결정을 기록한다. 명확한 거절이 있으면 취소 결정을 기록하고, Try의 응답이 유실된 참여자도 취소 대상에 포함한다. 확정 결정을 내린 뒤 일부 Confirm이 실패하면 같은 식별자로 Confirm을 재시도한다.

타임아웃은 결과 미상으로 기록한다. 재시도 횟수와 백오프를 제한하고, 복구 작업이 오래된 `PENDING` 주문을 읽어 참가자 상태와 주문의 결정 기록을 대조하도록 한다. 예약 만료는 stale 상태의 조사 신호로 쓸 수 있다. 참가자 자체에서 자동 해제하려면 지연된 Confirm과 양립하는 별도 계약이 필요하다.

실패 검증에서는 마지막 재고 경쟁, Cancel이 Try보다 먼저 도착하는 상황, Confirm 커밋 뒤 응답 유실, 주문 서비스 재시작을 다룬다. 각 경우에 예약량, 가용량, 주문에 기록한 결정을 비교한다.

관련 문서 [Idempotent Order Processing in a Monolith](20_idempotent_order_processing_in_a_monolith.md) · [Orchestrating Order Sagas and Compensations](24_orchestrating_order_sagas_and_compensations.md)
