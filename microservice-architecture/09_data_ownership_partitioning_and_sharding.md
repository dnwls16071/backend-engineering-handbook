# Data Ownership, Partitioning, and Sharding

Database per Service는 데이터를 쓰고 스키마를 바꿀 권한을 정하는 패턴이다. 별도 DB 서버는 가능한 배치 방식 중 하나다. 같은 서버에서도 서비스별 스키마와 권한으로 소유권을 분리할 수 있으며, 서버 자원과 장애의 영향은 함께 받을 수 있다. [Database per Service](https://microservices.io/patterns/data/database-per-service)

## 저장소와 일관성의 선택

| 질문 | 판단 기준 |
| --- | --- |
| 관계형 DB와 다른 저장소 중 무엇을 쓰는가? | 로컬 트랜잭션, 질의 형태, 인덱스, 운영 인력을 비교한다. Polyglot Persistence는 요구가 다를 때 소유자마다 기술을 선택할 수 있게 한다. |
| 네트워크가 분리되면 어떤 결과를 허용하는가? | 재고 예약은 충돌을 피하려고 일부 요청을 거절하거나 대기할 수 있다. 상품 설명 조회는 계약이 허용하면 이전 값을 제공할 수 있다. |
| 같은 DB의 테이블 파티션이 필요한가? | 주로 특정 범위만 읽거나 오래된 데이터를 통째로 정리할 수 있는지 판단한다. |
| 여러 DB 인스턴스로 샤딩이 필요한가? | 단일 인스턴스의 저장량·쓰기 병목과 애플리케이션 라우팅·운영 비용을 비교한다. |

CAP 정리의 일관성은 단일 최신 복사본처럼 동작하는 성질에 관한 것이며, ACID의 C와 같은 뜻으로 사용하지 않는다. 정리는 분할 상황에서 해당 일관성과 가용성을 동시에 보장할 수 없다는 결과다. 실제 설계에서는 기능별로 허용할 실패와 오래된 데이터의 범위를 명시한다. [Gilbert와 Lynch · CAP 논문](https://dl.acm.org/doi/10.1145/564585.564601) · [MariaDB Partitioning Overview](https://mariadb.com/docs/server/server-usage/partitioning-tables/partitioning-overview)

## 두 MariaDB 샤드의 설계 검토

주문을 `customerId` 기준으로 분산하고 두 샤드만 사용하는 경우를 예로 들면, 정수 식별자에 대한 `floorMod(customerId, 2)`로 고객 42는 샤드 0, 고객 43은 샤드 1에 보낼 수 있다. 조회도 같은 규칙과 라우팅 키를 사용한다. 도메인의 저장소 계약은 “고객의 주문 저장·조회”로 표현하고, 어느 샤드를 고를지는 영속 어댑터가 처리한다.

고객 키가 없는 주문 조회는 라우팅 매핑이나 별도 읽기 모델이 필요할 수 있다. 고객별 집중도, 전역 ID, 테넌트 유일 제약, 샤드 장애와 재분배를 함께 검토한다. 샤드 수를 나머지 연산의 분모로 직접 쓰면 개수가 늘 때 많은 키의 위치가 바뀐다. 운영에서 확장이 예상되면 가상 버킷 매핑이나 이동 절차를 먼저 설계한다. 서비스 간 조회는 [CQRS와 읽기 모델](10_cross_service_queries_cqrs_and_event_sourcing.md)에서 이어서 다룬다. [Chris Richardson · Scale Cube](https://microservices.io/articles/scalecube.html)
