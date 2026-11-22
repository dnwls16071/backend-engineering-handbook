# Handling Order Repository Failures

주문 저장소는 조회 결과 없음, 입력이 제약에 걸린 경우, 저장 실패를 서로 다른 결과로 다룰 수 있다. 저장 기술 예외를 어느 수준에서 변환할지 먼저 정한다. [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html) · [Spring 6.2 DAO Support](https://docs.spring.io/spring-framework/reference/6.2/data-access/dao.html)

## 1. 조회 없음과 쓰기 실패를 구분한다

JPA EntityManager.find는 행이 없으면 null을 반환한다. 저장 포트는 이를 Optional.empty로 표현할 수 있다. 주문번호 고유 제약에 걸린 쓰기는 업무 충돌인지 기술 오류인지 실제 위반 제약과 호출 문맥을 대조한다. [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Spring 6.2 DAO Support](https://docs.spring.io/spring-framework/reference/6.2/data-access/dao.html) · [Martin Fowler · Repository](https://martinfowler.com/eaaCatalog/repository.html)

## 2. 실패가 확정되는 위치를 확인한다

DB 오류가 persist 호출에서 바로 보이지 않고 flush나 커밋에서 나타날 수 있다. 저장 메서드 내부에서만 잡겠다는 가정은 피하고 트랜잭션 종료 경로까지 테스트한다. [Jakarta Persistence 3.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring 6.2 Transaction Strategies](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/strategies.html)
