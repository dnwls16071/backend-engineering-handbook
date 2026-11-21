# Entity Identifiers and Hibernate Sequence Optimizers

식별자 전략은 행의 정체성을 표현하는 방법과 키를 언제 어떤 비용으로 확보할지를 결정한다. 엔티티 INSERT를 측정할 때는 식별자를 가져오는 SQL도 포함한다. [Hibernate 식별자 매핑](https://docs.hibernate.org/orm/6.6/userguide/html_single/#identifiers)

## 1. JPA와 Hibernate의 엔티티 식별자

| 방식 | 키를 확보하는 방법 |
| --- | --- |
| 할당 키 | 호출자가 `persist()` 전에 `@Id`를 채운다 |
| `IDENTITY` | DB가 INSERT에서 키를 생성한다. Hibernate의 일반 엔티티 INSERT 배치가 비활성화된다 |
| `SEQUENCE` | DB 시퀀스에서 INSERT 전에 값을 확보할 수 있다 |
| `TABLE` | 별도 테이블에서 키를 예약한다. 해당 행의 접근과 갱신 비용을 확인한다 |
| `UUID` | JPA 3.1의 생성 전략이다. Hibernate의 기본 UUID 생성은 JVM에서 수행한다 |
| `AUTO` | 구현체와 환경에 따라 적절한 전략을 결정한다. JPA 3.1에서 `java.util.UUID` 필드는 `UUID` 전략과 같다 |

업무에서 사용하는 자연 키가 변경될 가능성이 있으면 대리 키를 PK로 사용하고 자연 키에는 `UNIQUE` 제약을 둔다. 복합 PK가 모델의 정체성이라면 `@EmbeddedId`나 `@IdClass`로 매핑하고 키의 동등성과 해시 코드를 일치시킨다. [Jakarta Persistence 3.1 §2.4와 §11.1.20](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1) · [Hibernate JDBC 배치](https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch-session-batch)

## 2. Hibernate 시퀀스 최적화

Hibernate의 시퀀스 옵티마이저는 여러 식별자를 JVM에서 배정해 DB 시퀀스 호출을 줄인다. 예를 들어 `pooled-lo`에서 시퀀스가 1, 21, 41을 반환하고 할당 단위가 20이면 1–20, 21–40, 41–60을 예약한다. `pooled`는 일반적으로 소스 값을 구간 상한으로 해석하며 초기값은 별도로 처리한다. 최적화가 꺼진 경우에는 일반적으로 각 식별자에 소스 호출이 필요하다. [Hibernate 옵티마이저](https://docs.hibernate.org/orm/6.6/userguide/html_single/#identifiers-optimizers)

```java
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_id_gen")
@SequenceGenerator(name = "order_id_gen", sequenceName = "order_id_seq", allocationSize = 20)
private Long id;
```

```sql
CREATE SEQUENCE order_id_seq START WITH 1 INCREMENT BY 20;
```

예제에서 `hibernate.id.optimizer.pooled.preferred=pooled-lo`를 적용하면 구간 하한 방식으로 검증할 수 있다. DB의 `INCREMENT BY`와 Hibernate가 가정하는 증가량을 함께 관리한다. 여러 애플리케이션 인스턴스가 공유한다면 모두 같은 시퀀스 규약을 사용해야 한다. 시퀀스의 DB 내부 `CACHE` 옵션은 Hibernate의 `allocationSize`와 별개이며, 롤백과 프로세스 재시작 이후에도 연속 번호를 전제할 수 없다. [Hibernate pooled-lo 매핑 예제](https://docs.hibernate.org/orm/6.6/userguide/html_single/#identifiers-optimizer-pooled-lo) · [PostgreSQL CREATE SEQUENCE](https://www.postgresql.org/docs/17/sql-createsequence.html)
