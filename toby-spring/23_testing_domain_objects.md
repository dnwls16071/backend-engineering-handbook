# Testing Domain Objects

도메인 객체에 있는 상태 전이와 불변식은 객체의 입력과 출력으로 검증한다. 예를 들어 취소된 Order에는 확정 전이를 허용하지 않는 규칙을 둘 수 있다. [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 1. 정상 전이와 금지 전이를 함께 검사한다

생성 직후 주문과 취소된 주문을 각각 준비하고 같은 확정 동작을 실행한다. 성공 상태, 거절 결과와 거절 뒤 기존 상태가 유지되는지를 검사한다. 시간 조건이 있으면 고정 시계나 명시적 입력 시각을 사용한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html) · [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html)

## 2. 영속성과 연동은 다른 범위에서 검증한다

객체 자체의 규칙은 Spring이나 데이터베이스를 띄우지 않고 검증할 수 있다. 같은 전이가 재조회 후 보존되는지와 동시 쓰기 경쟁은 별도의 통합 테스트로 확인한다. [Martin Fowler · Anemic Domain Model](https://martinfowler.com/bliki/AnemicDomainModel.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
