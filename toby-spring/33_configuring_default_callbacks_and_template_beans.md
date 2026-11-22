# Configuring Default Callbacks and Template Beans

자주 쓰는 실행자와 추출기 조합은 템플릿 빈의 기본값으로 제공한다. 호출마다 특수한 조합이 필요한 경우 별도 인자로 넘길 수 있는 경로를 둔다. [Spring 6.2 @Bean](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/bean-annotation.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 1. 기본 전략을 구성 코드에서 조립한다

@Bean 메서드에 ApiExecutor와 ExRateExtractor를 인자로 받아 템플릿을 생성한다. 제공자별 후보가 많다면 기본값의 의도를 빈 설정에 드러낸다. [Spring 6.2 @Bean](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/bean-annotation.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)

## 2. 공유 빈에 요청별 데이터를 보관하지 않는다

빈에는 공통 클라이언트와 불변 설정을 두고 URI·응답은 지역 값으로 넘긴다. 기본 인자 경로와 호출자가 직접 전달한 경로를 각각 검사한다. [Spring 6.2 Bean Scopes](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html) · [Martin Fowler · Mocks Aren’t Stubs](https://martinfowler.com/articles/mocksArentStubs.html)
