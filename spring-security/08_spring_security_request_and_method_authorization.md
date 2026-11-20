# Spring Security Request and Method Authorization

## 1. 요청 매처로 접근 범위 설정하기

`authorizeHttpRequests`의 규칙은 선언 순서대로 평가된다. 구체적인 경로와 메서드를 먼저 두고, 마지막 규칙으로 나머지 요청의 정책을 정한다. 예를 들어 `GET /catalog/items`에는 `catalog:read`를, `POST /catalog/items`에는 `catalog:write`를 요구할 수 있다. 공개 정적 리소스에 `permitAll()`을 지정하면 해당 요청에도 보안 필터 체인이 적용되어 보안 헤더를 유지할 수 있다. [Spring Security 6.5 · Authorize HttpServletRequests](https://docs.spring.io/spring-security/reference/6.5/servlet/authorization/authorize-http-requests.html)

| 규칙 | 판정 |
| --- | --- |
| `permitAll()` | 인증 상태와 관계없이 허용 |
| `authenticated()` | 인증을 요구 |
| `fullyAuthenticated()` | 기억하기 인증보다 높은 수준의 인증을 요구 |
| `hasAuthority("catalog:write")` | 문자열과 일치하는 권한을 요구 |
| `hasRole("ADMIN")` | 기본 접두사를 사용하면 `ROLE_ADMIN` 권한을 요구 |
| `denyAll()` | 요청을 거부 |

## 2. 서비스 메서드에 인가 적용하기

`@EnableMethodSecurity`를 활성화하면 `@PreAuthorize`가 붙은 서비스 메서드는 프록시 진입 시 인가를 확인한다. 요청 경로와 별개로 호출 가능한 쓰기 서비스에 같은 권한 정책을 적용할 수 있다. 조건에 메서드 인자나 리소스 소유권을 사용할 때는 서버가 확인한 객체와 현재 인증 정보를 기준으로 판단한다. [Spring Security 6.5 · Method Security](https://docs.spring.io/spring-security/reference/6.5/servlet/authorization/method-security.html)

```java
import org.springframework.security.access.prepost.PreAuthorize;

public class CatalogEditor {

    @PreAuthorize("hasAuthority('catalog:write')")
    public String renamePreview(String name) {
        return name.strip();
    }
}
```

위 클래스를 Spring 빈으로 등록하고 프록시를 통해 호출한다. `@PostAuthorize`는 메서드 반환 이후에 결과에 대한 접근을 검사할 수 있다. 변경 작업을 막아야 하는 조건은 실행 전에 평가한다. `@PreFilter`와 `@PostFilter`는 컬렉션의 요소를 대상으로 필터링할 수 있다. [Spring Security 6.5 · 메서드 인가 애너테이션](https://docs.spring.io/spring-security/reference/6.5/servlet/authorization/method-security.html)

## 3. 역할 계층의 적용 범위 정하기

`RoleHierarchy`로 `ROLE_ADMIN > ROLE_EDITOR`처럼 상위 역할에 도달 가능한 하위 역할을 선언할 수 있다. 계층을 보고 판정하는 인가 매니저나 표현식 처리기에 연결해야 하며, HTTP와 메서드 인가에서 같은 계층이 필요한지 각각 확인한다. [Spring Security 6.5 · Hierarchical Roles](https://docs.spring.io/spring-security/reference/6.5/servlet/authorization/architecture.html)
