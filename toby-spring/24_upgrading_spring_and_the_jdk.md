# Upgrading Spring and the JDK

업그레이드 실습은 Spring Framework 6.2와 Java 21 조합을 예로 든다. 업그레이드 전에는 현재 버전과 목표 버전의 공식 호환 범위를 비교한다. [Spring Framework 6.x Upgrade Guide](https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x) · [JDK 21 Migration Guide](https://docs.oracle.com/en/java/javase/21/migrate/)

## 1. 빌드와 실행의 버전을 맞춘다

빌드 도구가 선택하는 Java toolchain, 컴파일 대상 버전, 테스트·CI·서버 실행 버전을 확인한다. Spring 6 계열의 Java 17 기준선 및 Jakarta API 네임스페이스에 맞는 모듈을 고른다. [Spring Framework 6.x Upgrade Guide](https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x) · [JDK 21 Migration Guide](https://docs.oracle.com/en/java/javase/21/migrate/)

## 2. 기존 계약을 재검증한다

변경 전 테스트 통과 여부를 확인하고, 빌드·빈 초기화·HTTP 요청·DB 트랜잭션 테스트를 다시 실행한다. 리팩터링은 호환성 변경의 원인을 확인할 수 있도록 별도 단계에서 진행한다. [JDK 21 Migration Guide](https://docs.oracle.com/en/java/javase/21/migrate/) · [JUnit 5.12.2 User Guide](https://docs.junit.org/5.12.2/user-guide/) · [Spring 6.2 Transactional Tests](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html)
