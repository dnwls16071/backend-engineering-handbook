# Spring Security Fundamentals for OAuth 2.0

## 1. 초기화에서 요청 처리까지

Spring Boot는 의존성과 사용자 설정에 따라 서블릿 보안 자동 구성을 적용한다. `SecurityFilterChain` 빈은 `HttpSecurity`에 등록된 configurer를 바탕으로 만들어진다. `FilterChainProxy`는 요청마다 처음 매치된 체인 하나를 실행하므로, 브라우저 로그인과 API 인증을 별도 체인에 둘 수 있다. [Spring Boot 3.5 · Spring Security](https://docs.spring.io/spring-boot/3.5/reference/web/spring-security.html) · [Spring Security 6.5 · Servlet Architecture](https://docs.spring.io/spring-security/reference/6.5/servlet/architecture.html) · [필터 체인의 초기화](01_spring_security_initialization_and_filter_chains.md)

| 단계 | 처리 |
| --- | --- |
| 인증 | 필터가 자격 증명을 추출하고 `AuthenticationManager`에 검증을 맡긴다. |
| 컨텍스트 | 인증 결과를 `SecurityContext`에 연결해 이후 필터에서 쓸 수 있게 한다. |
| 인가 | `AuthorizationFilter`가 현재 요청의 정책을 평가한다. |
| 응답 | 인증을 시작해야 할 때는 `AuthenticationEntryPoint`가, 접근이 거부된 경우에는 해당 처리기가 응답을 만든다. |

## 2. 인증 수단마다 다른 진입점

HTTP Basic의 진입점은 일반적으로 `401`과 인증 챌린지 헤더를 보낸다. OAuth 로그인에서는 브라우저를 로그인 경로로 유도할 수 있다. Bearer 토큰 API에서는 `WWW-Authenticate: Bearer`가 인증 요구를 전달한다. 선택한 체인의 진입점이 클라이언트가 처리할 수 있는 응답을 내는지 확인한다. [Spring Security 6.5 · HTTP Basic](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/passwords/basic.html) · [Spring Security 6.5 · OAuth2 Login](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/login/core.html) · [Spring Security 6.5 · Bearer Tokens](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/bearer-tokens.html)

## 3. 브라우저가 호출하는 경로

교차 출처 호출에 필요한 CORS 사전 요청은 인증 판정보다 앞에서 처리한다. OAuth 리다이렉트는 브라우저의 탐색이고, JavaScript가 다른 출처의 API를 호출할 때는 CORS 설정이 관여한다. 세션 쿠키로 상태를 변경하는 엔드포인트에는 [CSRF 보호](07_spring_security_cors_csrf_and_samesite.md)도 적용한다. [Spring Security 6.5 · CORS](https://docs.spring.io/spring-security/reference/6.5/servlet/integrations/cors.html)
