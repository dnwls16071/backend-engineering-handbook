# Spring Security Initialization and Filter Chains

## 1. 초기화에서 만들어지는 객체

Spring Boot에서 `spring-boot-starter-security`를 추가하면 서블릿 웹 보안의 기본 구성이 적용된다. `SecurityFilterChain` 빈을 등록하면 그 체인의 필터와 접근 규칙을 직접 정할 수 있다. 기본 사용자 자동 구성은 체인 자동 구성과 조건이 다르므로 사용자 저장소나 `AuthenticationProvider`의 등록 여부도 따로 확인한다. [Spring Boot 3.5 · Spring Security](https://docs.spring.io/spring-boot/3.5/reference/web/spring-security.html)

| 객체 | 역할 |
| --- | --- |
| `SecurityBuilder` | 설정을 모아 최종 보안 객체를 생성한다. |
| `SecurityConfigurer` | 초기화와 구성 단계에서 공유 객체, 필터, 규칙을 등록한다. |
| `HttpSecurity` | 특정 서블릿 요청에 사용할 `SecurityFilterChain`을 구성한다. |
| `WebSecurity` | 여러 체인을 모아 요청을 보낼 `FilterChainProxy`를 구성한다. |

`HttpSecurity`에 연결된 configurer는 공유 객체가 필요한 초기화와 실제 필터를 구성하는 단계를 거친다. `http.build()`가 끝나면 매처와 필터 목록을 가진 체인이 생성된다. [Spring Security 6.5 · Java Configuration](https://docs.spring.io/spring-security/reference/6.5/servlet/configuration/java.html) · [Spring Security 6.5 API · HttpSecurity](https://docs.spring.io/spring-security/reference/6.5/api/java/org/springframework/security/config/annotation/web/builders/HttpSecurity.html)

## 2. HTTP 요청이 체인으로 들어가는 흐름

```text
서블릿 컨테이너 → DelegatingFilterProxy → springSecurityFilterChain(FilterChainProxy)
               → 처음으로 매치된 SecurityFilterChain의 필터들 → 애플리케이션
```

`DelegatingFilterProxy`는 컨테이너의 필터 호출을 Spring 빈에 연결한다. `FilterChainProxy`는 여러 체인 중 처음으로 매치된 체인 하나를 실행한다. `securityMatcher(...)`는 체인 자체가 적용되는 요청을 정한다. `authorizeHttpRequests(...)` 안의 `requestMatchers(...)`는 선택된 체인에서 적용할 인가 규칙을 고른다. [Spring Security 6.5 · Servlet Architecture](https://docs.spring.io/spring-security/reference/6.5/servlet/architecture.html) · [Spring Security 6.5 · HTTP Security](https://docs.spring.io/spring-security/reference/6.5/servlet/configuration/java.html)

## 3. 카탈로그의 기본 체인 등록하기

아래 예제는 공개 안내 경로를 열고 카탈로그에 로그인을 요구한다. 사용자 조회는 별도로 등록한 `UserDetailsService` 또는 Boot가 제공한 기본 사용자에 연결할 수 있다.

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

import static org.springframework.security.config.Customizer.withDefaults;

@Configuration(proxyBeanMethods = false)
@EnableWebSecurity
public class CatalogSecurity {

    @Bean
    SecurityFilterChain catalogChain(HttpSecurity http) throws Exception {
        return http
                .authorizeHttpRequests(rules -> rules
                        .requestMatchers("/welcome", "/assets/**").permitAll()
                        .requestMatchers("/catalog/**").authenticated()
                        .anyRequest().denyAll())
                .formLogin(login -> login.permitAll())
                .logout(withDefaults())
                .build();
    }
}
```

애플리케이션 시작 로그의 체인과 필터 목록을 보면 어떤 인증 또는 인가 필터가 구성됐는지 확인할 수 있다. 체인이 여러 개라면 [다중 보안 설정](11_advanced_spring_security_configuration.md)에서 요청별 선택 순서를 확인한다. [Spring Security 6.5 · Security Filters](https://docs.spring.io/spring-security/reference/6.5/servlet/architecture.html)
