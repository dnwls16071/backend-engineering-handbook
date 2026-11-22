# Automating Repeatable Tests

자동화 테스트는 예상 결과를 코드로 비교해 같은 조건에서 반복할 수 있게 한다. 출력 로그를 사람이 눈으로 확인하던 계산부터 검증 가능한 테스트로 만든다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html)

## 1. 성공과 실패를 자동으로 판단한다

업무 결과를 단언하고 예상이 어긋나면 테스트가 실패하게 한다. 테스트 메서드 이름은 입력 조건과 기대 동작을 드러낸다. 실행 환경, 시간과 외부 응답이 필요한 경우 통제 가능한 값으로 준비한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Java 21 Clock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Clock.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)

## 2. 재실행으로 발견할 문제를 정한다

값을 고치거나 경계를 리팩터링할 때 같은 테스트를 실행한다. 테스트 순서를 바꿔도 결과가 같은지, 실패 메시지로 원인을 찾을 수 있는지 확인한다. [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html)
