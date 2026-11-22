# Extracting Variable Behavior into Methods

변하는 코드는 어느 제공자를 쓰는지에 따라 달라지는 작업이다. 예를 들어 API 주소 구성과 응답 필드 해석에 다른 규약이 적용될 수 있다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 1. 변화하는 부분을 이름 있는 메서드로 옮긴다

buildUri와 extractRate처럼 의도를 나타내는 이름을 붙이고, 필요한 인자와 반환값을 명시한다. 값이나 오류를 새로 해석하는 변경은 기존 동작 추출과 다른 단계로 둔다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Spring 6.2 REST Clients](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html)

## 2. 다른 제공자 사례를 대입한다

주소만 바뀌는 경우와 응답 구조가 달라지는 경우를 비교한다. 변화가 독립적이라면 이후 각각을 별도 협력자로 꺼내는 근거가 된다. [Martin Fowler · Extract Function](https://refactoring.com/catalog/extractFunction.html) · [Robert C. Martin · Open–Closed Principle](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html)
