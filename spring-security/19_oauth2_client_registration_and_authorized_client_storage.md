# OAuth 2.0 Client Registration and Authorized Client Storage

## 1. Boot 설정을 클라이언트 등록으로 연결하기

`spring.security.oauth2.client.registration`은 애플리케이션에서 사용할 등록을 정의하고, `provider`는 인가 서버의 세부 정보를 설정한다. 아래에서 `catalog-ui`는 Spring이 선택하는 등록 ID이고, `client-id`는 인가 서버가 클라이언트를 식별하는 값이다. 비밀 값은 환경 설정에서 주입한다. [Spring Security 6.5 · ClientRegistration](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/core.html)

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          catalog-ui:
            provider: catalog-id
            client-id: catalog-portal
            client-secret: ${CATALOG_CLIENT_SECRET}
            client-authentication-method: client_secret_basic
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
            scope: [openid, profile, catalog.read]
        provider:
          catalog-id:
            issuer-uri: https://id.example.com
```

Spring Boot는 등록 속성이 있을 때 이를 읽어 `ClientRegistrationRepository`를 구성할 수 있다. 내장 로그인 페이지에서 로그인 링크를 만들 때와 콜백에서 등록을 찾을 때 모두 등록 ID가 사용된다. [Spring Boot 3.5 · OAuth2 Client](https://docs.spring.io/spring-boot/3.5/reference/web/spring-security.html) · [Spring Security 6.5 · OAuth2 Login Core Configuration](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/login/core.html)

## 2. 등록 정보와 실행 중 상태 구분하기

| 모델 | 저장하거나 조회하는 값 |
| --- | --- |
| `ClientRegistrationRepository` | 클라이언트 ID, 공급자, 범위 등 정적인 등록 정보 |
| `AuthorizationRequestRepository` | 브라우저 콜백이 돌아올 때 사용할 인가 요청 상태 |
| `OAuth2AuthorizedClient` | 등록, 주체 이름, 액세스 토큰, 발급된 경우 리프레시 토큰 |
| `OAuth2AuthorizedClientRepository` | 서블릿 요청에 연계해 승인된 클라이언트를 저장하고 조회 |
| `OAuth2AuthorizedClientService` | 등록 ID와 주체 이름을 기준으로 승인된 클라이언트를 관리 |

콜백을 처리할 서버가 최초 요청과 다른 경우에도 인가 요청 상태에 접근할 수 있어야 한다. 발급 토큰의 저장 위치를 고를 때는 토큰 수명, 삭제, 여러 인스턴스에서의 읽기 범위를 함께 정한다. [Spring Security 6.5 · Core Interfaces and Classes](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/core.html) · [Spring Security 6.5 · Authorization Request Repository](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/authorization-grants.html)
