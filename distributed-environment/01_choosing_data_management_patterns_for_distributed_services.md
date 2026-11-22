# Choosing Data Management Patterns for Distributed Services

주문·재고·상품 검색을 분리할 때는 데이터의 소유 서비스, 각 요청에 필요한 일관성, 한 저장소가 감당할 수 있는 부하를 각각 결정한다. [Microsoft · Microservice Data Considerations](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations) · [Microsoft · Sharding](https://learn.microsoft.com/en-us/azure/architecture/patterns/sharding)

## 1. CAP는 통신이 끊겼을 때 요청별로 적용한다

CAP의 일관성은 원자적 읽기·쓰기(선형화 가능성)를, 가용성은 장애가 없는 노드에 들어온 요청이 결국 응답을 받는 보장을 가리킨다. 네트워크 분할이 가능하면 이 두 보장을 모든 실행에서 동시에 만족시킬 수 없다. 이 모델의 가용성은 운영에서 측정하는 성공률이나 응답 시간 목표와 구분한다. [Gilbert·Lynch · CAP](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf)

예를 들어 재고 예약은 권한 있는 재고 사본과 통신이 끊기면 요청을 거절하거나 나중에 재시도하게 한다. 상품 검색은 정한 최신성 한도 안에서 마지막 반영 값을 제공할 수 있다. 두 경로에 허용되는 실패 응답과 복구 후 정합성 검사를 따로 정한다. [Gilbert·Lynch · CAP](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf) · [Microsoft · Microservice Data Considerations](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations)

## 2. 저장소 소유권과 기술 선택을 구분한다

| 패턴 | 적용 기준 | 검토 비용 | 근거 |
| --- | --- | --- | --- |
| Database per Service | 재고 서비스가 재고 스키마와 쓰기 규칙을 소유한다. 주문 서비스는 공개 API나 이벤트를 사용한다. | 서비스 간 조인 대신 API 조합이나 조회 모델이 필요할 수 있다. | [AWS · Database-per-Service](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-data-persistence/database-per-service.html) · [Microsoft · Microservice Data Considerations](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations) |
| Polyglot Persistence | 주문 정본에는 트랜잭션을, 검색에는 색인과 전문 검색을 우선하는 저장소를 고려한다. | 검색 사본의 최신성, 재구축 및 여러 기술의 운영 비용을 관리한다. | [Microsoft · Microservice Data Considerations](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations) |
| Sharding | 테넌트나 식별자를 기준으로 행을 나누고, 각 요청이 어느 샤드로 갈지 정한다. | 핫 샤드, 여러 샤드 조회·트랜잭션, 재분할을 검증한다. | [Microsoft · Sharding](https://learn.microsoft.com/en-us/azure/architecture/patterns/sharding) |

## 3. 샤딩 전후에 병목 가설을 검증한다

먼저 저장량과 쓰기 부하가 단일 저장소의 실제 한계에 닿는지 측정한다. 테넌트별 조회가 많으면 테넌트 키로 라우팅하는 안을 검토하되, 한 테넌트에 쓰기가 몰릴 때의 분포와 전체 조회 비용도 함께 측정한다. 복제는 같은 데이터의 사본을 두는 선택이고, 샤딩은 데이터 집합을 나누는 선택이다. [Microsoft · Sharding](https://learn.microsoft.com/en-us/azure/architecture/patterns/sharding)
