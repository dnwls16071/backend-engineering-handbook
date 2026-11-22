# Loading Spring Configuration in Different Ways

구성 클래스로 컨텍스트를 만들거나, 빈 컨텍스트에 구성 클래스를 등록한 뒤 초기화할 수 있다. 컴포넌트 스캔은 지정한 패키지에서 설정과 컴포넌트를 찾는 또 다른 등록 방식이다. [Spring 6.2 AnnotationConfigApplicationContext](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/instantiating-container.html)

## 1. 생성과 등록 순서를 구분한다

AnnotationConfigApplicationContext(Config.class)는 구성 클래스를 받아 초기화를 진행한다. 무인자 생성자를 쓰는 경우 register 또는 scan으로 메타데이터를 등록한 뒤 refresh를 호출한다. [Spring 6.2 AnnotationConfigApplicationContext](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/instantiating-container.html)

## 2. 탐색 범위와 실행 결과를 검증한다

스캔은 기준 패키지를 명시해 실험용 구성이나 같은 타입의 다른 구현이 들어오지 않게 한다. 소규모 테스트는 필요한 구성 클래스만 등록하고 최종 빈 타입과 실제 기능을 검사할 수 있다. [Spring 6.2 AnnotationConfigApplicationContext](https://docs.spring.io/spring-framework/reference/6.2/core/beans/java/instantiating-container.html) · [Spring 6.2 DI](https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html)
