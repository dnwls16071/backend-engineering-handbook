# Spring Authorization Server Protocol Endpoints

## 1. 인가와 토큰 발급에 사용하는 엔드포인트

경로는 루트 issuer와 Spring Authorization Server 1.5 기본 설정을 예로 든다. 배포 계약에는 `AuthorizationServerSettings`와 서버 메타데이터에 실제로 노출되는 주소를 사용한다. [Spring Authorization Server · Configuration Model](https://docs.spring.io/spring-authorization-server/reference/configuration-model.html) · [Spring Authorization Server · Protocol Endpoints](https://docs.spring.io/spring-authorization-server/reference/protocol-endpoints.html)

| 기본 경로 | 역할 |
| --- | --- |
| `/oauth2/authorize` | 브라우저의 인가 요청을 처리하고 사용자 인증이나 동의를 진행한다. |
| `/oauth2/token` | 인가 코드 교환, 클라이언트 자격 증명, 리프레시 요청 등을 처리한다. |
| `/oauth2/par` | 지원하는 구성에서는 인가 파라미터를 먼저 제출하고 `request_uri`를 받는다. |
| `/oauth2/device_authorization` | 기기 인증 흐름을 사용하는 클라이언트에 기기 코드와 사용자 코드를 제공한다. |
| `/oauth2/introspect` | 인증된 호출자에게 토큰 활성 상태와 공개 가능한 정보를 제공한다. |
| `/oauth2/revoke` | 호출자가 폐기할 수 있는 토큰의 무효화를 요청한다. |
| `/oauth2/jwks` | `JWKSource`가 설정되면 검증에 쓸 공개 키 세트를 제공한다. |
| `/.well-known/oauth-authorization-server` | OAuth 인가 서버의 issuer와 지원 엔드포인트를 게시한다. |

인가 요청이 도착하면 서버가 등록된 클라이언트, 콜백, 지원 범위와 필요한 PKCE 설정을 검사한다. 코드 교환에서는 발급된 코드가 해당 클라이언트와 요청에 연결되는지 확인한다. 엔드포인트 설정에서 요청 변환기, 검증기, 인증 제공자, 응답 핸들러를 필요에 따라 확장할 수 있다. [RFC 6749 · Authorization Code](https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1) · [RFC 9126 · PAR](https://www.rfc-editor.org/rfc/rfc9126.html) · [RFC 8628 · Device Authorization Grant](https://www.rfc-editor.org/rfc/rfc8628.html) · [Spring Authorization Server · Protocol Endpoints](https://docs.spring.io/spring-authorization-server/reference/protocol-endpoints.html)

## 2. OIDC를 활성화한 경우

| 기본 경로 | 역할 |
| --- | --- |
| `/.well-known/openid-configuration` | OIDC 공급자 메타데이터를 게시한다. |
| `/userinfo` | 액세스 토큰으로 확인한 사용자 클레임을 반환한다. |
| `/connect/logout` | 공급자에서의 로그아웃 흐름을 처리한다. |
| `/connect/register` | 동적 클라이언트 등록을 활성화한 배포에서 사용한다. |

OIDC는 기본 인가 서버 구성에서 추가로 활성화한다. 동적 클라이언트 등록은 별도 설정이 필요하다. `/userinfo`는 리소스 요청으로 처리되므로 토큰 검증에 필요한 디코더와 발급 자원 설정을 확인한다. [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html) · [Spring Authorization Server · OpenID Connect Endpoints](https://docs.spring.io/spring-authorization-server/reference/protocol-endpoints.html)

## 3. 토큰을 폐기했을 때의 영향 확인하기

토큰 폐기는 인가 서버의 토큰 상태를 바꾼다. 인트로스펙션으로 확인하는 API는 인가 서버 상태에 따라 결과가 달라진다. 서명과 클레임만 로컬에서 확인하는 API에서는 발급자 상태를 추가로 확인하도록 설계하지 않은 경우 기존 JWT를 만료 때까지 허용할 수 있다. 어떤 방식에서 언제 무효화가 반영되는지 [리소스 서버 구성](27_oauth2_opaque_tokens_and_introspection.md)과 함께 확인한다. [RFC 7009 · Token Revocation](https://www.rfc-editor.org/rfc/rfc7009.html) · [RFC 7662 · Token Introspection](https://www.rfc-editor.org/rfc/rfc7662.html)
