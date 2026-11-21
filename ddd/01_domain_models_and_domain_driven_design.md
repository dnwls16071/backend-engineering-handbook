# Domain Models and Domain-Driven Design

도메인 모델은 업무 문제를 해결하는 데 필요한 개념, 관계, 규칙을 표현한다. 모델은 용어집, 대화, 상태 전이, 코드, 테스트에 같은 의미로 드러나야 한다. 예를 들어 회원 가입에서 “가입됨”이 이메일 인증 전 상태까지 포함하는지 먼저 합의해야 가입과 활성화를 별도 행동으로 설계할 수 있다. [Eric Evans · Domain-Driven Design Reference](https://www.domainlanguage.com/ddd/reference/)

## 1. 업무 언어를 모델로 만들기

| 업무에서 확인할 질문 | 모델에서 드러낼 결정 |
| --- | --- |
| 가입을 신청하면 언제부터 서비스를 이용할 수 있는가? | 가입 신청과 활성화의 상태를 각각 명명하고, 활성화 조건을 표현한다. |
| 회원이 같은 이메일을 다시 쓰면 어떻게 되는가? | 이메일 비교 기준, 유일성의 범위, 동시 요청에서 충돌을 처리할 위치를 정한다. |
| 강의 운영에서 말하는 강사는 언제부터 강의를 개설할 수 있는가? | 회원 자격과 강사 승인 상태의 의미와 관계를 각각 정의한다. |

**유비쿼터스 언어**(Ubiquitous Language)는 모델을 바탕으로 도메인 전문가와 개발자가 함께 쓰는 언어다. 업무 표현을 코드에 옮긴 뒤에도 예외 사례를 통해 의미를 계속 점검한다. `activateMember`가 이메일 검증을 전제로 한다면 API, 도메인 메서드, 테스트에서 같은 전제를 읽을 수 있어야 한다.

## 2. Bounded Context와 도메인 모델의 책임

**Bounded Context**는 특정 모델과 용어가 일관된 의미를 갖는 경계다. 예를 들어 회원 관리에는 가입과 계정 상태가 중요하고, 강의 운영에는 강사 승인과 소속이 중요할 수 있다. 각 경계가 어떤 상태를 소유하는지 정하고, 다른 경계에는 필요한 식별자와 계약만 공개한다. 같은 배포 단위 안에서도 이런 경계를 둘 수 있다. 실제로 한 모델로 충분한지는 함께 바뀌는 규칙과 팀의 업무 언어를 기준으로 판단한다. [Eric Evans · Bounded Context와 Context Map](https://www.domainlanguage.com/ddd/reference/)

DDD의 전략적 설계는 모델의 범위와 맥락 간 관계를 다룬다. 전술적 설계는 그 범위 안에서 엔티티, 값 객체, 애그리거트 같은 도구로 업무 규칙을 표현한다. 도메인 모델 패턴은 상태와 행동을 객체에 함께 둔다. 업무가 단순하다면 절차 중심의 Transaction Script로도 충분할 수 있으며, 반복되거나 복잡해지는 규칙에는 모델을 도입할 이유가 생긴다. [Martin Fowler · Domain Model](https://martinfowler.com/eaaCatalog/domainModel.html) · [Transaction Script](https://martinfowler.com/eaaCatalog/transactionScript.html)

## 3. 모델을 발전시키는 순서

1. 성공 시나리오와 업무가 거절되는 대표 사례를 함께 적는다.
2. 허용된 상태 전이와 언제나 성립해야 하는 불변식을 도출한다.
3. 규칙을 판단하는 객체와 판단에 필요한 사실을 정한다.
4. 모델을 바꾸고, 업무 용어로 읽히는 테스트로 다시 확인한다.

[회원 도메인 모델](02_modeling_members_with_entities_and_value_objects.md)은 이 과정을 회원의 상태와 값에 적용한다. [포트와 어댑터](03_designing_a_hexagonal_member_application.md)는 그 모델을 HTTP와 저장소에서 호출하거나 저장하는 경계를 다룬다.
