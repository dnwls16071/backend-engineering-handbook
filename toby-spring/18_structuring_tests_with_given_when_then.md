# Structuring Tests with Given–When–Then

테스트마다 초기 조건, 호출, 관찰 결과를 나누면 실패 원인을 좁히기 쉽다. Given은 데이터와 협력자, When은 실행할 동작, Then은 보장할 계약이다. [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/)

## 1. 계산 테스트의 세 요소를 고른다

| 요소 | 환율 테스트 예 | 근거 |
| --- | --- | --- |
| Given | 미화 2단위와 단위당 1,300원의 환율을 준비한다. | [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html) · [Java 21 BigDecimal](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) |
| When | 결제 준비를 한 번 호출한다. | [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html) |
| Then | 환산 금액이 2,600원인지 검증한다. | [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) |

## 2. 관찰 가능한 결과에 의도를 담는다

반환값이나 상태 변화처럼 호출자가 관찰하는 결과를 먼저 단언한다. 외부 발행이 계약에 포함될 때는 호출 횟수나 전달 대상을 추가로 검증한다. [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html) · [Martin Fowler · Given When Then](https://martinfowler.com/bliki/GivenWhenThen.html)
