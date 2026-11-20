# Spring Security Session Management

## 1. 세션 생성 정책

| 정책 | Spring Security의 세션 사용 |
| --- | --- |
| `ALWAYS` | HTTP 세션을 생성한다. |
| `IF_REQUIRED` | 보안 기능에 필요할 때 생성한다. |
| `NEVER` | 새 세션 생성은 피하고 이미 존재하는 세션은 사용할 수 있다. |
| `STATELESS` | HTTP 세션에서 `SecurityContext`를 복원하거나 세션에 저장하지 않도록 구성한다. |

`STATELESS`는 보안 컨텍스트의 세션 사용에 대한 설정이다. 애플리케이션의 다른 코드나 별도로 등록한 기능은 세션을 사용할 수 있다. 요청마다 토큰으로 인증하는 구성에서는 저장소 및 요청 캐시 설정도 함께 확인한다. [Spring Security 6.5 · Stateless Authentication](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/session-management.html) · [HTTP 세션의 동작](../spring-mvc/12_login_with_cookies_and_http_sessions.md)

## 2. 로그인하면서 세션 식별자 바꾸기

인증 전부터 있던 세션을 로그인에 이어 쓰는 경우 식별자를 갱신해 세션 고정을 방지한다. 현대 서블릿 컨테이너에서 기본 전략은 `changeSessionId()`를 사용해 세션 객체를 유지하면서 ID를 교체한다. `migrateSession`은 새 세션에 기존 속성을 복사하고, `newSession`은 보안 처리에 필요한 일부 속성만 이어 간다. [Spring Security 6.5 · Session Fixation Protection](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/session-management.html)

## 3. 동시 로그인 수 제한하기

`sessionManagement(session -> session.maximumSessions(1))`은 사용자별 동시 세션 수를 제한한다. 새 로그인이 허용되는 설정에서는 기존 세션을 만료 대상으로 표시하고, 해당 세션의 후속 요청에서 `ConcurrentSessionFilter`가 만료를 처리할 수 있다. 기존 세션을 유지해야 하는 업무라면 `maxSessionsPreventsLogin(true)`로 새 로그인을 거절한다. `SessionRegistry`에 등록된 세션 정보가 실제 만료·종료와 일치하도록 세션 수명 이벤트를 연결한다. 공식 예제의 `HttpSessionEventPublisher` 등록이 그 역할을 한다. [Spring Security 6.5 · Concurrent Session Control](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/session-management.html)

Spring Security 6의 기본 흐름에서는 인증 메커니즘이 성공 시 `SessionAuthenticationStrategy`를 호출한다. 이전 구성에서 쓰이던 `SessionManagementFilter`는 기본 체인에 자동으로 들어오지 않는다. [직접 만든 로그인](04_spring_security_authentication_persistence.md)에서도 이 전략이 적용되는지 확인한다. [Spring Security 6.5 · Moving Away From SessionManagementFilter](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/session-management.html)
