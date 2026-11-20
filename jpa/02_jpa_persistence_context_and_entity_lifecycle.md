# JPA Persistence Context and Entity Lifecycle

영속성 컨텍스트는 `EntityManager`가 엔티티 인스턴스를 추적하는 범위다. 같은 컨텍스트 안에서는 같은 엔티티 타입과 기본 키에 대응하는 관리 인스턴스를 하나로 유지한다.

## 1. 엔티티 상태

| 상태 | 특징 | 상태를 바꾸는 동작 |
| --- | --- | --- |
| 비영속 | 생성했지만 컨텍스트에 등록되지 않았다. | `new`로 만든 후 `persist()`로 관리 상태로 전환 |
| 영속 | 컨텍스트가 변경 사항을 관리한다. | `persist()` 또는 `find()` |
| 준영속 | 식별자는 있지만 현재 컨텍스트에서 관리하지 않는다. | `detach()`, `clear()`, `close()` |
| 삭제 | 관리 중인 엔티티가 삭제 대상으로 등록됐다. | `remove()` 후 플러시에서 DB 반영 |

`merge()`는 넘긴 객체의 상태를 새로운 또는 기존 관리 인스턴스로 복사해 반환한다. 준영속 객체의 수정을 이어가려면 반환된 관리 인스턴스를 사용한다. [Jakarta Persistence 3.1 · 엔티티 생명주기](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a1929) · [Jakarta Persistence 3.1 · 준영속 상태 병합](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#merging-detached-entity-state)

## 2. 1차 캐시와 변경 감지

같은 컨텍스트에서 같은 ID를 `find()`로 두 번 조회하면 관리 중인 같은 인스턴스를 받을 수 있다. 1차 캐시는 이 컨텍스트 안에서 동작한다. JPQL로 검색할 때는 조건에 맞는 ID나 값을 구하기 위해 SQL이 실행될 수 있으며, 엔티티 결과에는 같은 컨텍스트의 관리 인스턴스가 재사용될 수 있다. [Jakarta Persistence 3.1 · 영속성 컨텍스트](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a11432)

```java
Workspace first = em.find(Workspace.class, id);
Workspace second = em.find(Workspace.class, id);

// first == second
first.rename("Platform Engineering");
em.flush();
```

영속 엔티티는 별도 `update()` 호출 없이도 변경 감지의 대상이 된다. 삽입, 수정, 삭제 SQL은 플러시 시점까지 미뤄질 수 있다. `IDENTITY`처럼 DB가 값을 만드는 식별자 전략에서는 활성 트랜잭션에서 ID를 얻기 위해 삽입이 더 일찍 실행될 수 있다.

## 3. 플러시와 커밋

| 동작 | 효과 |
| --- | --- |
| `flush()` | 컨텍스트의 변경을 DB와 동기화한다. 트랜잭션은 계속된다. |
| `commit()` | 필요한 플러시를 수행하고 트랜잭션을 완료한다. |
| `clear()` | 모든 관리 엔티티를 분리한다. 아직 플러시하지 않은 변경은 반영되지 않을 수 있다. |
| `refresh(entity)` | 관리 엔티티의 상태를 DB 값으로 다시 읽는다. 메모리의 수정 내용은 덮어쓴다. |

기본 `FlushModeType.AUTO`에서는 변경 사항이 쿼리 결과에 영향을 주는 경우 구현체가 조회 전에 이를 반영한다. `FlushModeType.COMMIT`은 커밋 시 동기화하며, 그 전에 실행한 쿼리 결과에 미반영 변경이 포함될지는 보장되지 않는다. SQL이 이미 실행됐어도 활성 트랜잭션에서 롤백하면 그 트랜잭션의 DB 변경을 취소할 수 있다. [Jakarta Persistence 3.1 · DB 동기화](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a1955) · [Jakarta Persistence 3.1 · 쿼리와 플러시 모드](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a4374)
