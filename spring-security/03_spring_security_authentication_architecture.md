# Spring Security Authentication Architecture

## 1. 인증 요청과 인증 결과

`Authentication`은 인증 요청과 인증 결과를 표현한다. 폼 필터는 처음에 제출된 사용자 이름과 자격 증명으로 인증 요청을 만든다. 검증을 마친 결과에는 일반적으로 `principal`과 `GrantedAuthority` 목록이 들어간다. 현재 보안 컨텍스트는 `SecurityContextHolder`로 찾을 수 있고, 기본 전략은 현재 스레드에 연결된 `ThreadLocal`이다. [Spring Security 6.5 · Servlet Authentication Architecture](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/architecture.html)

| 구성 요소 | 역할 |
| --- | --- |
| `AuthenticationManager` | 인증 요청을 받아 결과를 반환하거나 인증 예외를 던진다. |
| `ProviderManager` | 요청 타입을 처리할 수 있는 `AuthenticationProvider`에 인증을 위임한다. |
| `AuthenticationProvider` | 지원하는 인증 타입에 대해 검증한다. |
| `SecurityContext` | 현재 `Authentication`을 담는다. |
| `SecurityContextHolder` | 현재 실행 경로에서 컨텍스트를 읽고 설정하는 진입점이다. |

`ProviderManager`는 인증 제공자가 지정된 토큰 타입을 지원하는지 `supports(...)`로 확인한다. 커스텀 제공자를 추가할 때는 지원 타입과 거부 조건을 분명히 하고, 검증에 성공한 경우에만 인증된 토큰을 반환한다. [Spring Security 6.5 · ProviderManager와 AuthenticationProvider](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/architecture.html)

## 2. 사용자 이름과 비밀번호 검증하기

`DaoAuthenticationProvider`는 `UserDetailsService`로 사용자 정보를 조회하고, `PasswordEncoder`로 제출한 비밀번호와 저장된 해시를 비교한다. `UserDetails`는 사용자 이름, 저장된 비밀번호 형식, 권한, 계정 상태 등을 제공한다. 계정 잠금, 비활성화, 만료처럼 계정 상태를 나타내는 값도 인증 결과에 영향을 준다. [Spring Security 6.5 · DaoAuthenticationProvider](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/passwords/dao-authentication-provider.html)

비밀번호를 저장할 때는 `PasswordEncoder.encode(...)`로 단방향 해시를 생성한다. `DelegatingPasswordEncoder`의 `{id}...` 형식은 저장된 해시에 사용할 알고리즘을 식별하게 해 준다. 인증 후에는 `ProviderManager`가 지원하는 결과 객체의 자격 증명을 기본적으로 지울 수 있으므로, 인증 결과나 감사 로그에 원래 비밀번호를 보관할 필요가 없다. [Spring Security 6.5 · Password Storage](https://docs.spring.io/spring-security/reference/6.5/features/authentication/password-storage.html) · [Spring Security 6.5 · ProviderManager](https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/architecture.html)
