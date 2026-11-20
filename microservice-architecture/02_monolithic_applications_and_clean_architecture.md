# Monolithic Applications and Clean Architecture

한 애플리케이션을 단일 배포 단위로 운영하면 호출이 짧고, 같은 데이터베이스에서 함께 보호할 수 있는 변경을 로컬 트랜잭션으로 처리하기 쉽다. 배포 일정과 리소스 확장은 애플리케이션 단위로 묶인다. 패키지와 모듈을 어떻게 구성하느냐에 따라 단일 배포에서도 변경 범위를 제어할 수 있다. [Fowler · Monolith First](https://martinfowler.com/bliki/MonolithFirst.html)

## 하나의 배포 단위 안에 업무 경계 두기

주문과 재고를 한 프로세스에 둔 상황을 가정한다. 주문 도메인은 주문 생성과 확정 조건을 책임지고, 재고 모듈은 가용 수량과 예약을 책임진다. 같은 DB에 있어도 각 테이블에 대한 쓰기는 소유 모듈을 통해 이뤄지게 한다. 두 변경을 함께 커밋해야 하는지는 현재 업무 불변식과 공유 트랜잭션의 범위를 확인해 결정한다.

## Clean Architecture의 의존성 규칙

| 책임 | 주문 예 |
| --- | --- |
| 엔티티 | 주문의 상태와 확정 조건을 표현한다. |
| 유스케이스 | 주문 등록을 조율하고 필요한 저장·조회 능력을 포트로 요청한다. |
| 인터페이스 어댑터 | HTTP 요청·응답, DB 행을 내부 계약으로 변환한다. |
| 프레임워크와 조립 | 컨트롤러, 데이터베이스, 트랜잭션 설정을 연결한다. |

컴파일 시 의존성은 정책이 있는 안쪽을 향한다. 유스케이스는 출력 포트를 호출하고 저장 어댑터는 그 포트를 구현한다. 실행 시 호출은 DB 어댑터에 도달할 수 있으므로 호출 방향과 소스 코드 의존 방향을 구분한다. [Robert C. Martin · The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

주문 생성 테스트는 유스케이스 입력과 결과에 집중하고, 실제 테이블 제약과 트랜잭션은 영속 어댑터 테스트로 확인한다. 패키지를 업무 기능별로 재구성할 때는 [모듈러 모놀리스](03_modular_monoliths_with_hexagonal_boundaries.md)에서 공개 계약과 내부 타입을 정한다. [모놀리식 아키텍처 유형](../architecture-style/01_four_types_of_monolithic_architecture.md)
