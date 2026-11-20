# Modeling Members with Entities and Value Objects

회원 도메인 모델은 회원의 정체성, 현재 상태, 가능한 행동을 함께 표현한다. 이 문서에서는 가입 후 이메일을 검증해 활성화하고, 이용 정지 후 정책에 따라 복구할 수 있는 회원을 예로 든다.

## 1. 정체성, 값, 상태 전이

| 구성 | 설계 기준 | 회원 모델에서의 역할 |
| --- | --- | --- |
| 엔티티 | 속성이 바뀌어도 정체성을 유지한다. | `Member`는 이메일이나 표시 이름이 바뀌어도 여전히 같은 회원이다. |
| 식별자 | 동일 객체를 찾거나 다른 경계에서 참조할 수 있다. | `MemberId`는 생성 시 부여하는 불변 값으로 설계한다. |
| 값 객체 | 속성의 값으로 동등성을 판단하고 자체 유효성을 지킨다. | `EmailAddress`는 이 시스템의 형식과 비교 기준을, `DisplayName`은 표시 이름 제약을 표현한다. |

값 객체는 일반적으로 불변으로 둔다. 정규화는 업무가 동일하다고 판단하는 범위에서 정의한다. 이메일 변경이 가능한 모델에서는 이메일을 `Member`의 지속적인 정체성으로 쓰기 어렵다. [Eric Evans · Entity와 Value Object](https://www.domainlanguage.com/ddd/reference/) · [Martin Fowler · Value Object](https://martinfowler.com/bliki/ValueObject.html)

| 행동 | 시작 상태 | 결과와 규칙 |
| --- | --- | --- |
| 가입 신청 | 회원 생성 전 | 새 `MemberId`로 `PENDING` 회원을 만든다. |
| 활성화 | `PENDING` | 등록된 주소의 검증이 완료된 경우에만 `ACTIVE`가 된다. |
| 이용 정지 | `ACTIVE` | `SUSPENDED`로 변경한다. |
| 이용 재개 | `SUSPENDED` | 재개 조건을 만족하고 현재 이메일이 검증되어 있으면 `ACTIVE`로 돌아간다. |

`setStatus`를 여러 호출 지점에 노출하면 상태 전이 규칙이 흩어진다. `activate`, `suspend`, `resume`과 같이 업무 행동을 메서드로 표현하면 각 메서드에서 출발 상태와 조건을 확인할 수 있다. 상태를 추가할 때는 먼저 허용과 거절 사례를 보완하고, 반복되는 조건만 의미 있는 이름으로 추출한다. [Martin Fowler · Domain Model](https://martinfowler.com/eaaCatalog/domainModel.html)

## 2. 값이 없다는 의미와 검증 위치

회원이 존재하지 않는 조회 결과와, 존재하는 회원에서 선택 항목이 비어 있는 상태는 다른 계약이다. 전자는 저장소 포트가 `Optional<Member>` 등으로 표현할 수 있다. 후자는 명시적 nullable 타입이나 도메인 값으로 표현한다. 객체 생성에 꼭 필요한 값은 생성 경계에서 확인한다.

Spring Framework 7의 JSpecify 방식에서는 `@NullMarked` 범위에 기본 null 계약을 두고, 허용하는 자리에 `@Nullable`을 표시한다. 이는 정적 검사 도구의 근거다. 런타임 요청 형식은 Bean Validation으로 검사하고, 상태 전이와 값 객체 규칙은 도메인에서 보호한다. 중요 값은 객체 생성 시 검증해 웹 이외의 호출 경로에도 같은 규칙을 적용한다. [Spring Null-safety](https://docs.spring.io/spring-framework/reference/core/null-safety.html) · [JSpecify User Guide](https://jspecify.dev/docs/user-guide/)

## 3. 테스트에서 모델의 언어 사용하기

- 이메일 검증 전에는 활성화할 수 없다.
- 다른 회원의 검증 결과로 활성화할 수 없다.
- 정지된 회원은 재개 조건을 만족해야 다시 활성화된다.
- 표시 이름을 바꿔도 회원의 정체성은 유지된다.

이메일 중복처럼 여러 회원에 걸친 규칙은 단일 `Member`가 판단할 수 있는 상태와 분리한다. [회원 애플리케이션 경계](03_designing_a_hexagonal_member_application.md)에서 중복 조회와 저장 제약의 역할을 정리한다.
