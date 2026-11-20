# Spring Transaction Proxies and Rollback Rules

## 1. 트랜잭션 프록시가 적용되는 호출 보기

`@Transactional`이 설정된 Spring 빈을 프록시를 통해 호출하면 트랜잭션 어드바이스가 대상 메서드 실행 전후에 동작한다. 일반적인 서비스에서는 클래스에 기본 설정을 두고, 일부 메서드에 다른 설정을 선언할 수 있다. 더 구체적인 메서드 설정이 적용된다. `TransactionSynchronizationManager.isActualTransactionActive()`로 현재 스레드에서 실제 트랜잭션이 활성화됐는지 확인할 수 있다. [Spring Framework 6.2 · @Transactional](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html) · [Spring Framework 6.2 API · TransactionSynchronizationManager](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/transaction/support/TransactionSynchronizationManager.html)

같은 객체 안의 `this.save(...)` 호출은 기본 프록시 모드에서 메서드에 선언된 트랜잭션 어드바이스를 거치지 않는다. 따로 경계가 필요한 작업은 다른 빈의 메서드로 옮겨 프록시를 통해 호출할 수 있다. 빈의 `@PostConstruct`에서 초기 데이터를 저장해야 할 때는 프록시 초기화가 끝난 뒤 실행되는 경로에서 트랜잭션 서비스 빈을 호출한다. [Spring Framework 6.2 · 프록시 모드에서의 호출과 초기화](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html) · [Spring AOP의 자기 호출](../spring-advanced/12_spring_aop_proxy_limitations_and_self_invocation.md)

## 2. 메서드별 옵션 고르기

| 옵션 | 의미 |
| --- | --- |
| `propagation` | 호출 시 기존 트랜잭션이 있을 때 참여 또는 새로 시작할지 정한다. |
| `isolation` | 새 트랜잭션에 사용할 격리 수준을 정한다. 기본값은 데이터베이스 설정을 따른다. |
| `timeout` | 새 트랜잭션의 제한 시간을 초 단위로 지정한다. |
| `readOnly` | 매니저와 데이터 접근 구현체에 읽기 전용 의도를 전달한다. 쓰기 제한을 강제하는지는 구현에 따라 다르다. |
| `transactionManager` | 여러 매니저가 있을 때 적용할 매니저를 선택한다. |
| `rollbackFor`, `noRollbackFor` | 메서드 밖으로 전파된 예외에 적용할 롤백 규칙을 선언한다. |

이미 열린 트랜잭션에 참여할 때는 바깥 트랜잭션의 격리 수준과 제한 시간이 적용된다. 참여 방식은 [전파 기본](15_spring_transaction_propagation_modes.md)에서 다룬다. [Spring Framework 6.2 · 트랜잭션 전파](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/tx-propagation.html)

## 3. 업무 예외에 커밋과 롤백 규칙 연결하기

기본 규칙은 경계를 넘어 나온 `RuntimeException`과 `Error`에서 롤백한다. 체크 예외는 기본 규칙에서 커밋 대상이다. 예를 들어 상품 등록에 필수인 재고 확인이 체크 예외로 실패한다면 `@Transactional(rollbackFor = InventoryCheckException.class)`처럼 해당 타입을 지정할 수 있다. 정상 반환한 메서드의 결과는 커밋 절차로 이어지며, 이미 롤백 전용으로 표시됐거나 실제 커밋이 실패하면 오류가 호출자에게 전달된다. [Spring Framework 6.2 · 롤백 규칙](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/rolling-back.html)

재고가 없음을 기록하고 등록 요청을 보류하는 업무라면 그 결과를 서비스 반환값으로 표현할 수 있다. 데이터 제약 위반 등 복구할 수 없는 실패는 예외를 경계 밖으로 전달하고, 호출자는 서비스 호출이 완료된 뒤 사용자 응답을 결정한다. [Spring Framework 6.2 · 선언적 트랜잭션 롤백](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/rolling-back.html)
