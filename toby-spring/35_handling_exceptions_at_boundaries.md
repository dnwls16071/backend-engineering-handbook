# Handling Exceptions at Boundaries

예외 처리의 첫 선택은 지금 계층에서 의미 있는 대응을 할 수 있는지 판단하는 일이다. 전환, 전파, 복구는 서로 다른 책임을 가지며 오류를 감추면 호출자가 끝난 작업을 성공으로 오해할 수 있다. [Java 21 JLS Exceptions](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html) · [Spring 6.2 DAO Support](https://docs.spring.io/spring-framework/reference/6.2/data-access/dao.html)

## 1. 상황별 대응을 정한다

다시 진행할 수 있다면 그 조건을 확인하고 재시도한다. 상위 계층이 의미를 알 수 있도록 예외를 변환할 때는 원인을 남긴다. Java의 checked 여부는 컴파일 시 선언·처리 규칙이고, 복구 가능성은 호출 계약에서 별도로 정한다. [Java 21 JLS Exceptions](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html) · [Spring 6.2 DAO Support](https://docs.spring.io/spring-framework/reference/6.2/data-access/dao.html)

## 2. 트랜잭션과 오류 계약을 연결한다

메서드 안에서 예외를 잡고 정상 반환하면 바깥 트랜잭션 프록시는 원래 예외를 보지 못할 수 있다. 롤백해야 한다면 예외 정책에 맞게 전파하거나 명시적으로 rollback-only를 표시한다. [Spring 6.2 Rollback](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/rolling-back.html) · [Spring 6.2 TransactionTemplate](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/programmatic.html)
