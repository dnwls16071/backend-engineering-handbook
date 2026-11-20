# Decomposing Services by Domain Boundaries

서비스 분해의 출발점은 업무 능력과 모델의 소유권이다. 웹·서비스·저장소처럼 기술 계층으로 잘라 원격 호출로 연결하면 하나의 업무 변경이 여러 서비스에 걸칠 수 있다. [Decompose by business capability](https://microservices.io/patterns/decomposition/decompose-by-business-capability.html) · [Decompose by subdomain](https://microservices.io/patterns/decomposition/decompose-by-subdomain.html)

## 이커머스 경계 후보

| 영역 | 소유하는 결정 | 경계 밖에 제공할 정보 |
| --- | --- | --- |
| 카탈로그 | 상품 설명, 판매 조건 및 표시 가격 | 상품 조회, 유효한 가격 견적 |
| 주문 | 주문 항목·금액 스냅샷과 주문 상태 | 주문 조회, 주문 확정·취소 사실 |
| 재고 | 재고 가용 여부와 예약 수명 | 예약 요청의 결과와 예약 ID |
| 결제 | 결제 승인·취소와 거래 상태 | 승인 식별자와 결제 결과 |

주문에 저장하는 가격은 주문 시 받아들인 견적의 일부다. 현재 상품 표시 가격이 바뀌어도 이미 접수한 주문의 가격을 덮지 않는다. 카탈로그의 현재 상태와 주문의 이력은 서로 다른 계약에 따라 바뀐다.

## 경계를 검증하는 세 가지 질문

1. **어떤 규칙이 함께 바뀌는가.** 변경 이력과 팀의 언어에서 응집도를 확인한다.
2. **무엇을 같은 커밋에서 지켜야 하는가.** 재고 초과 판매를 방지하는 예약 규칙은 재고 쪽이 보호한다. 주문 전체가 진행되는 동안의 일관성은 주문 상태·보상으로 표현할 수 있다.
3. **어떤 호출이 반복적으로 경계를 왕복하는가.** 주문 한 건마다 상대 서비스에 여러 세부 API를 부르면 데이터 소유권이나 계약 단위를 다시 검토한다.

분해 이후에는 각 Context의 데이터 출처, API·이벤트 방향, 허용 지연을 Context Map에 기록한다. 다른 시스템의 용어를 그대로 들이기 어려우면 Anti-Corruption Layer에서 자기 모델의 의미로 번역한다. 경계가 불분명한 영역은 [모듈 계약](03_modular_monoliths_with_hexagonal_boundaries.md)으로 먼저 검증할 수 있다. [Eric Evans · Context Map과 Anti-Corruption Layer](https://www.domainlanguage.com/ddd/reference/)
