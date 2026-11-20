# OpenID Connect and ID Tokens

## 1. OAuth 2.0 위에 로그인 결과 연결하기

OpenID Connect(OIDC)는 OAuth 2.0 흐름에 사용자 인증 정보를 추가한다. 클라이언트인 Relying Party가 `openid` 범위를 요청하고, 공급자인 OpenID Provider는 클라이언트가 확인할 수 있는 ID 토큰을 발급한다. `profile`과 `email`은 추가 사용자 정보를 요청하는 범위다. [OpenID Connect Core 1.0 · Authentication](https://openid.net/specs/openid-connect-core-1_0.html)

ID 토큰의 대상은 애플리케이션 클라이언트다. 리소스 서버에는 해당 API에 발급된 액세스 토큰을 보낸다. UserInfo 호출도 액세스 토큰을 사용한다. UserInfo 결과를 로그인 정보에 합칠 때는 `sub`가 ID 토큰의 `sub`와 일치하는지 확인한다. [OpenID Connect Core 1.0 · ID Token and UserInfo](https://openid.net/specs/openid-connect-core-1_0.html)

## 2. ID 토큰 검증 항목

| 클레임 또는 정보 | 확인할 내용 |
| --- | --- |
| `iss` | 등록한 공급자의 issuer와 일치하는가 |
| `aud` | 이 클라이언트의 `client_id`를 포함하는가 |
| `exp` | 토큰이 유효 기간 안에 있는가 |
| `nonce` | 인가 요청에 넣었다면 결과의 값과 일치하는가 |
| 서명과 키 | 흐름에 적용되는 규칙대로, 신뢰한 공급자의 키와 허용 알고리즘으로 확인했는가 |

사용자를 시스템에 연결할 때는 issuer와 `sub`의 쌍을 기준으로 삼을 수 있다. 이메일은 표시와 연락에 사용하고, 이메일을 확인했다는 주장이 필요한 경우 `email_verified`의 의미와 공급자 정책을 함께 확인한다. [OpenID Connect Core 1.0 · ID Token Validation and Claims](https://openid.net/specs/openid-connect-core-1_0.html)

## 3. 공급자 메타데이터에서 엔드포인트 찾기

OIDC Discovery의 `.well-known/openid-configuration`은 인가, 토큰, UserInfo, 공개 키 세트 등 공급자 설정을 찾는 데 사용된다. Spring Security에서는 [클라이언트 등록](19_oauth2_client_registration_and_authorized_client_storage.md)의 `issuer-uri`로 연결할 수 있다. [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html) · [Spring Security 6.5 · OAuth2 Login Core Configuration](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/login/core.html)
