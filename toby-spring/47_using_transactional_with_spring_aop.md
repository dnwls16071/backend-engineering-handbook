# Using @Transactional with Spring AOP

@Transactional은 메서드 실행에 적용할 트랜잭션 속성을 선언한다. Spring의 프록시 모드에서는 외부 호출이 프록시를 지나야 해당 속성이 적용된다. [Spring 6.2 @Transactional](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html) · [Spring 6.2 AOP Proxying](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)

## 1. 유스케이스 경계에 속성을 선언한다

일반적으로 서비스의 진입 메서드에 선언한다. 인터페이스 기반 프록시에서는 인터페이스에서 노출하는 호출을 사용하고, 클래스 기반 프록시에서도 final 메서드나 self-invocation으로 별도 조언을 기대하지 않는다. [Spring 6.2 @Transactional](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html) · [Spring 6.2 AOP Proxying](https://docs.spring.io/spring-framework/reference/6.2/core/aop/proxying.html)

## 2. 롤백 규칙을 업무 예외에 맞춘다

기본 규칙은 RuntimeException과 Error의 롤백이며, checked 예외를 롤백 대상으로 삼으려면 rollbackFor 등 설정을 명시한다. 성공과 예외를 호출해 DB 반영 결과를 확인하고, 테스트 프레임워크의 자동 롤백과 서비스의 롤백을 구분한다. [Spring 6.2 Rollback](https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/rolling-back.html) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
