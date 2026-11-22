# Creating an Object Factory

객체를 만드는 규칙이 흩어지면 어떤 제공자가 실제 서비스에 연결되는지 파악하기 어렵다. 오브젝트 팩토리는 생성과 조립을 한곳에 둔다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 Java 구성](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/basic-concepts.html)

## 1. 팩토리에서 구성 결정을 모은다

ObjectFactory의 paymentService 메서드가 제공자와 서비스의 조합을 완성하도록 설계한다. 호출자는 완성된 서비스만 받는다. 공용 클라이언트처럼 재사용할 객체의 수명도 생성 책임과 함께 정한다. [Martin Fowler · Dependency Injection](https://martinfowler.com/articles/injection.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html) · [Spring 6.2 Bean Scopes](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html)

## 2. 팩토리와 컨테이너의 책임을 비교한다

직접 작성한 팩토리는 메서드가 실행될 때마다 무엇을 만들지 코드가 결정한다. Spring으로 옮기면 @Bean 메타데이터와 스코프로 생성과 조회의 규칙을 선언할 수 있다. [Spring 6.2 Java 구성](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/basic-concepts.html) · [Spring 6.2 Bean Scopes](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html)
