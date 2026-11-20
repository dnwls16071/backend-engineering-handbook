# JPA Mapping and Entity Identity in Domain Models

회원의 정체성, 데이터베이스의 행 식별자, 외부에서 조회하는 업무 키는 각각 다른 요구에서 나온다. 컬럼 하나로 여러 역할을 맡길 수도 있고, 각 역할을 분리할 수도 있다.

## 1. 도메인 ID, 기본 키, 자연 키

| 역할 | 회원 모델에서 확인할 질문 |
| --- | --- |
| 도메인 식별자 `MemberId` | 저장 전에도 안정된 ID가 필요한가? 다른 애그리거트가 어떤 값으로 참조하는가? |
| JPA `@Id`와 DB 기본 키 | DB에서 행을 어떻게 식별하고, 그 키를 언제 할당하는가? |
| 업무 자연 키 | 업무 자체에서 유일한 값이 있는가? 변경 가능성과 유일 범위가 무엇인가? |

예를 들어 불변 `MemberId`를 애플리케이션에서 생성해 기본 키로 쓰면 저장 전후의 식별자가 같다. DB 생성 키를 별도로 두고 `MemberId`에 유일 제약을 줄 수도 있다. 변경 가능한 이메일은 로그인이나 조회에 쓸 수 있으며, 지속적인 동일성에는 불변 식별자를 사용한다. Hibernate의 `@NaturalId`는 자연 키 매핑을 표현하는 확장이다. 운영 스키마에는 업무의 유일성과 null 허용 여부를 제약으로 명시한다. [Jakarta Persistence 3.2](https://jakarta.ee/specifications/persistence/3.2/) · [Hibernate · Natural IDs](https://docs.hibernate.org/stable/orm/introduction/html_single/)

## 2. 도메인 모델과 매핑의 결합 수준

| 방식 | 얻는 점 | 부담 |
| --- | --- | --- |
| 도메인 엔티티에 JPA 매핑 | 같은 객체에 업무 동작과 변경 감지를 적용할 수 있다. | JPA 생성·접근 규칙과 로딩 시점이 모델 설계에 영향을 준다. |
| 같은 클래스를 `orm.xml`에서 매핑 | 자바 클래스에서 매핑 메타데이터를 옮길 수 있다. | 같은 객체를 JPA가 관리하므로 생성자, 접근 방식, 프록시 등 런타임 제약이 적용된다. |
| 별도의 영속 엔티티와 변환기 | 도메인의 타입·구조를 영속 엔티티와 독립적으로 구성할 수 있다. | 왕복 변환, 버전 전달, 자식 변경 반영, 조회 비용을 검증해야 한다. |

JPA 표준 매핑을 사용할 때는 엔티티의 선언 요건, 기본 생성자와 필드·프로퍼티 접근 방식을 함께 확인한다. 저장된 데이터를 다시 읽었을 때 도메인 객체의 상태와 값 객체가 올바르게 복원되는지 검증한다. 별도 영속 모델을 둔다면 도메인 객체로 읽은 뒤 처리하고 다시 저장하는 과정에서 낙관적 잠금에 필요한 버전도 보존한다. [Jakarta Persistence 3.2 · Entity와 XML mapping](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2)

## 3. equals와 hashCode의 수명 주기

엔티티 동등성이 필요하면 같은 회원인지 판단할 안정적인 키를 고른다. 표시 이름, 관계 컬렉션, 바뀔 수 있는 이메일을 비교에 넣으면 수정 후 `HashSet`에서 찾지 못하거나 프록시 비교 과정에서 로딩이 일어날 수 있다. 생성 시 할당되는 불변 `MemberId`나 실제 불변 자연 키는 저장 전후의 해시를 유지하기 쉽다.

DB가 ID를 생성한다면 ID가 없는 서로 다른 두 객체를 같다고 처리하지 않는다. 영속화 전후에 해시가 바뀌지 않도록 설계하거나, ID가 나오기 전에 해시 컬렉션에 넣지 않는 계약이 필요하다. 프록시·상속이 있는 모델에서는 타입 비교, 대칭성, 세션 밖 비교까지 확인한다. 모든 엔티티 계층에 같은 비교 구현을 적용하기보다 동일성 계약을 먼저 정한다. [Hibernate · Entity equality](https://docs.hibernate.org/stable/orm/introduction/html_single/) · [Java Object 계약](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Object.html)

검증에서는 신규 객체 둘, 같은 ID를 다른 영속성 컨텍스트에서 읽은 객체, 프록시와 실제 객체, 영속화 전후 컬렉션 조회를 각각 다룬다.
