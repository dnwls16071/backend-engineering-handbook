# OAuth 2.0 Opaque Tokens and Introspection

## 1. 토큰 유효성을 인가 서버에 확인하기

리소스 서버는 토큰을 인가 서버의 인트로스펙션 엔드포인트에 보내 사용 가능한 상태인지 확인할 수 있다. 불투명 토큰은 클라이언트와 API가 문자열 자체에서 클레임을 읽는 방식을 전제로 하지 않는다. RFC 7662 응답은 `active`를 제공하고, 활성 토큰에 대해 `scope`, `sub`, `exp` 등 호출자에게 공개할 수 있는 값을 보낼 수 있다. [RFC 7662 · Token Introspection](https://www.rfc-editor.org/rfc/rfc7662.html)

## 2. Spring Boot와 opaqueToken DSL 구성하기

`oauth2ResourceServer(server -> server.opaqueToken(withDefaults()))`에 아래 속성을 적용할 수 있다. 인트로스펙션을 호출하는 자격 증명은 API가 보호하고, 엔드포인트에는 HTTPS를 사용한다. [Spring Security 6.5 · Opaque Token Minimal Configuration](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/opaque-token.html)

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        opaquetoken:
          introspection-uri: https://id.example.com/oauth2/introspect
          client-id: catalog-api
          client-secret: ${CATALOG_INTROSPECTION_SECRET}
```

`OpaqueTokenAuthenticationProvider`는 `OpaqueTokenIntrospector`에 검사 요청을 위임한다. Spring의 기본 흐름에서는 `active` 응답을 확인하고 받은 범위를 `SCOPE_` 권한으로 연결한다. 리소스 바인딩이나 사용자 속성을 추가로 확인해야 하면 인가 서버와 응답 계약을 정하고 인트로스펙터를 감싸 검증할 수 있다. [Spring Security 6.5 · Configuring Introspection and Authorities](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/opaque-token.html)

## 3. 응답 지연과 폐기 반영 확인하기

요청마다 인트로스펙션을 하면 인가 서버 응답 시간과 가용성이 API에 영향을 준다. 응답을 캐시한다면 캐시 수명 동안 폐기된 토큰이 계속 허용될 수 있는지를 평가한다. 조회 실패나 비활성 응답을 승인으로 취급하지 않도록 오류 정책을 정하고, 정상·비활성·통신 오류를 각각 테스트한다. [RFC 7662 · Security Considerations](https://www.rfc-editor.org/rfc/rfc7662.html#section-4)
