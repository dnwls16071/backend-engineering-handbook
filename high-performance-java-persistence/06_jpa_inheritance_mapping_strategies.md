# JPA Inheritance Mapping Strategies

엔티티 상속의 매핑 전략은 다형 조회, FK 대상, 서브타입 전용 제약에 영향을 준다. 예시는 결제 수단을 카드와 계좌이체로 나누는 모델을 사용한다. [Jakarta Persistence 3.1 §2.12와 §2.13](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate 상속 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#entity-inheritance)

## 1. JPA 상속과 다형 조회

엔티티 계층의 루트에 `@Inheritance`로 매핑 전략을 지정한다. 명시하지 않으면 JPA의 기본값은 `SINGLE_TABLE`이다. `select p from Payment p` 같은 JPQL은 기본적으로 하위 엔티티도 포함한다. 스키마를 결정하기 전에 베이스 타입으로 읽는 호출과 특정 하위 타입으로 읽는 호출의 비율을 확인한다.

| 전략 | 저장 방식 | 다형 조회에서 나타나는 비용 |
| --- | --- | --- |
| `SINGLE_TABLE` | 공통 및 하위 속성을 한 테이블에 보관 | 보통 테이블 하나를 조회 |
| `JOINED` | 공통 속성은 루트, 하위 속성은 서브타입 테이블 | 서브타입 속성을 복원할 때 조인 |
| `TABLE_PER_CLASS` | 구체 엔티티별 테이블에 전체 속성을 보관 | Hibernate에서는 계층 조회에 UNION 계열 연산 |

## 2. Single Table Inheritance

`payment` 테이블에 공통 컬럼, 카드 전용 컬럼, 계좌이체 전용 컬럼을 함께 둔다. 카드가 아닌 행에도 카드용 컬럼이 있으므로 그 컬럼에 전역 NOT NULL을 걸면 다른 타입의 행을 저장하기 어렵다. PostgreSQL에서는 타입과 필수 속성을 함께 검사하는 CHECK 제약으로 서브타입 규칙을 표현할 수 있다. [Hibernate Single Table](https://docs.hibernate.org/orm/6.6/userguide/html_single/#entity-inheritance-single-table)

## 3. 판별 컬럼과 판별 값

판별 컬럼은 같은 테이블의 행을 어느 엔티티 클래스로 읽을지 결정한다. 루트에서 컬럼 이름을, 서브타입에서 저장할 값을 지정하면 클래스 이름을 바꿔도 저장 규약을 유지할 수 있다. 운영에서 판별 값이 바뀌면 기존 행을 마이그레이션해야 한다.

```java
@Entity
@Table(name = "payment")
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "payment_kind")
abstract class Payment {
    @Id
    Long id;
}

@Entity
@DiscriminatorValue("CARD")
class CardPayment extends Payment {
    String cardReference;
}
```

## 4. Joined Inheritance

`payment`는 공통 값과 PK를 저장하고, `card_payment`는 같은 키를 PK이자 `payment`의 FK로 사용한다. 서브타입의 필수 속성에 NOT NULL을 적용할 수 있다. 한 엔티티의 INSERT가 여러 테이블 작업을 포함할 수 있으며, 루트로 다형 조회할 때 서브타입을 결정하고 속성을 가져오는 조인을 확인한다. [Hibernate Joined Table](https://docs.hibernate.org/orm/6.6/userguide/html_single/#entity-inheritance-joined)

## 5. Table per Class Inheritance

카드와 계좌이체를 별도 테이블로 두고 각 테이블에 공통 속성까지 저장한다. 하위 타입 단독 조회는 자기 테이블로 끝날 수 있다. 루트 다형 조회에서 Hibernate가 생성한 UNION SQL과 각 테이블의 인덱스를 확인한다. 공통 FK 하나로 모든 서브타입을 참조하기 어렵고, JPA 3.1에서는 이 전략의 구현 지원이 선택 사항이다. [Hibernate Table per Class](https://docs.hibernate.org/orm/6.6/userguide/html_single/#entity-inheritance-table-per-class) · [Jakarta Persistence 3.1 §2.13.3](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)

## 6. Mapped Superclass

`@MappedSuperclass`는 ID, 버전, 생성 시각 같은 매핑을 여러 엔티티에 물려준다. 부모 자체는 엔티티가 아니므로 JPQL의 조회 루트로 사용할 수 없다. 공통 필드의 이름을 일부 엔티티에서 다르게 저장하려면 `@AttributeOverride`를 검토한다. [Jakarta Persistence 3.1 §2.12.2](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1)
