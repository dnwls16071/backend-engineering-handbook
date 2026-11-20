# Microservice Architecture Fundamentals

온라인 상점의 주문, 재고, 결제를 독립적으로 변경하고 운영하려면 어느 규칙과 데이터를 누가 책임지는지 먼저 정해야 한다. 이 시리즈는 같은 업무를 모놀리스, 모듈러 모놀리스, 마이크로서비스에서 어떻게 나눌지 비교한다. [Lewis와 Fowler · Microservices](https://martinfowler.com/articles/microservices.html)

## 도메인 경계와 배포 경계

| 구분 | 결정할 내용 | 주문 시스템에서의 예 |
| --- | --- | --- |
| Bounded Context | 어디에서 업무 용어와 모델이 일관된 의미를 가지는가 | 주문 확정과 결제 승인은 서로 다른 사실이다. |
| 모듈 경계 | 어느 코드를 함께 변경하고 어떤 계약을 공개하는가 | 주문 모듈은 재고 예약 계약을 통해 협력한다. |
| 서비스 경계 | 무엇을 독립적으로 배포·확장하고 장애에서 격리하는가 | 재고가 독립 운영 대상이 되면 별도 서비스 후보가 된다. |

DDD는 업무 모델의 경계를 찾는 데 쓰고, 헥사고날 아키텍처는 각 경계 안에서 업무 규칙과 어댑터의 관계를 설계하는 데 쓴다. 모듈화한 애플리케이션도 단일 배포 단위로 운영할 수 있다. Bounded Context의 개수에서 서비스의 개수가 자동으로 결정되는 것은 아니다. [Eric Evans · DDD Reference](https://www.domainlanguage.com/ddd/reference/) · [Cockburn · Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture)

## 증상에서 패턴 고르기

| 관찰한 문제 | 먼저 검토할 설계 |
| --- | --- |
| 작은 변경에도 여러 기능을 함께 수정한다. | 업무 능력별 모듈, 공개 포트와 내부 모델의 분리 |
| 특정 기능만 배포하거나 확장하기 어렵다. | 변경·부하가 집중되는 모듈의 분리 가능성과 운영 비용 |
| 외부 서비스 장애가 주문 요청을 계속 붙잡는다. | 지연 예산, 타임아웃, 격리, 업무 상태의 명시 |
| 서비스 간 로컬 트랜잭션 이후 후속 처리에 실패한다. | Saga, Transactional Outbox, 멱등 소비자 |

패턴을 선택할 때는 함께 바뀌는 기능, 반드시 같은 커밋에서 지킬 규칙, 장애 후 복구할 상태를 먼저 적는다. 전체 패턴의 관계는 [Microservice Architecture Pattern Language](https://microservices.io/patterns/)에서 확인할 수 있다. 도메인 경계의 기본 용어는 [DDD 기초](../ddd/01_domain_models_and_domain_driven_design.md)를 참고한다.
