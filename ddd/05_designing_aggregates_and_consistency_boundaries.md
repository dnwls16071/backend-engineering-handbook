# Designing Aggregates and Consistency Boundaries

애그리거트는 한 번의 업무 변경으로 일관되게 유지할 상태의 경계다. 애그리거트 루트가 변경 진입점을 소유하고, 외부는 내부 객체를 직접 수정하지 않는다. 어떤 데이터를 함께 읽는지보다 어떤 규칙이 같은 커밋에서 성립해야 하는지가 경계를 정한다. [Eric Evans · Aggregate](https://www.domainlanguage.com/ddd/reference/) · [Vaughn Vernon · Effective Aggregate Design](https://www.dddcommunity.org/library/vernon_2011/)

## 1. 회원 상세 정보의 경계 정하기

| 정보 | 경계를 고르는 이유 |
| --- | --- |
| 상태와 이메일 검증 정보 | 현재 등록된 이메일이 검증되어야 활성화할 수 있다면, 상태와 검증 대상은 회원 루트가 함께 보호한다. |
| 표시 이름과 소개 | 별도 식별자와 생명주기가 없다면 `MemberProfile`을 값 객체로 모델링하고 루트의 행동으로 교체할 수 있다. |
| 별도로 검토되는 프로필 | 독립된 승인·이력·갱신 주기가 있고 즉시 함께 바꿔야 하는 규칙이 없다면 애그리거트를 분리할 수 있다. |
| 강사 승인 상태 | 강의 운영의 별도 업무다. 회원과는 `MemberId`와 필요한 계약으로 연결한다. |

예를 들어 가입 대기 중 이메일을 바꾸면 이전 주소의 검증을 무효화하고, 활성화 시 현재 주소에 해당하는 검증을 다시 확인한다. 검증된 주소와 계정 상태를 서로 다른 트랜잭션에서 제각각 수정하면 이 규칙을 보장하기 어렵다. 조회 화면에서 두 정보를 함께 보여 주는 요구만 있다면 읽기 모델에서 조합할 수 있다. [Vaughn Vernon · Making Aggregates Work Together](https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_2.pdf)

## 2. 애그리거트와 유스케이스의 트랜잭션

회원의 프로필 변경을 처리할 때 애플리케이션 서비스는 루트를 불러오고 행동을 호출한 뒤 결과를 저장한다. 저장소 계약은 일반적으로 루트 단위로 구성한다. 자식 엔티티의 테이블이 별도로 있다면 그 테이블의 쓰기는 영속 어댑터 내부에서 처리할 수 있다.

같은 루트에 대한 두 쓰기가 충돌할 수 있다면 버전 검사를 둔다. JPA `@Version`은 버전이 관리되는 엔티티의 변경 충돌을 검출하는 데 사용한다. 자식만 수정했을 때 부모 버전이 모든 매핑에서 증가한다고 가정하지 않는다. 불변식 보호에 부모 버전이 필요하면 모델과 매핑에 맞는 갱신이나 잠금 방식을 택하고, 실제로 동시 변경을 검증한다. [Jakarta Persistence 3.2 · Optimistic Locking](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2)

## 3. 경계 밖의 참조와 일관성

다른 애그리거트는 보통 식별자로 참조한다. 한 변경에 여러 경계가 관여한다면 업무에 지연이 허용되는지 먼저 합의한다. 회원 상태를 검색 화면에 복제하는 작업은 지연을 허용할 수 있다. 정지 회원의 강의 개설을 즉시 막아야 한다면 오래된 조회 복제본에 의존할 수 있는지 별도로 판단하고, 검증과 쓰기 사이의 경쟁도 고려한다.

지연이 허용된 상태 전달에 이벤트를 쓸 때는 커밋 이후에만 외부에 알린다. 저장 성공 후 발행이 빠져도 복구해야 한다면 상태 변경과 아웃박스 레코드를 같은 트랜잭션에 저장하고 재발행을 처리한다. 수신자는 중복 전달과 버전 역전을 고려한다. [Vaughn Vernon · Aggregate 협력](https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_2.pdf) · [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
