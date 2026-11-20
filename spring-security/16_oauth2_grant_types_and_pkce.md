# OAuth 2.0 Grant Types and PKCE

## 1. 접근 권한을 얻는 흐름 고르기

| 유형 | 적합한 흐름 |
| --- | --- |
| Authorization Code | 사용자가 브라우저에서 승인하고, 클라이언트가 인가 코드를 토큰으로 교환한다. |
| Client Credentials | 기밀 클라이언트가 자신의 권한으로 API를 호출한다. |
| Refresh Token | 기존 권한 부여에서 발급한 리프레시 토큰으로 새 액세스 토큰을 요청한다. |
| Implicit | 브라우저 리다이렉트로 액세스 토큰을 전달하던 초기 방식이다. 현재 브라우저 로그인에는 코드 흐름과 PKCE를 사용한다. |
| Resource Owner Password Credentials | 애플리케이션이 사용자 비밀번호를 받아 전달하던 방식이다. 현재 OAuth 보안 모범 사례에서는 사용이 금지된다. |

클라이언트 자격 증명 흐름에서는 사용자 세션이나 ID 토큰을 전제로 삼지 않는다. 사용자 로그인은 [OIDC](17_openid_connect_and_id_tokens.md)와 코드 흐름을 사용한다. [RFC 6749 · Authorization Grants](https://www.rfc-editor.org/rfc/rfc6749.html#section-4) · [RFC 9700 · OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/rfc/rfc9700.html)

## 2. 인가 코드 교환을 PKCE와 연결하기

1. 클라이언트가 요청마다 `code_verifier`를 만들고, `S256`으로 변환한 `code_challenge`를 인가 요청에 담는다.
2. 사용자가 인가 서버에서 인증과 필요한 승인 절차를 거치면 등록된 리다이렉트 URI로 인가 코드가 돌아온다.
3. 클라이언트가 요청 상태를 확인한 뒤 코드와 원래의 `code_verifier`를 토큰 엔드포인트에 보낸다.
4. 인가 서버가 코드에 연결된 챌린지와 검증 값이 일치하는지 확인하고 토큰을 발급한다.

공개 클라이언트는 PKCE를 사용해야 하고, 기밀 클라이언트에도 PKCE가 권장된다. `state`를 사용하는 구성에서는 원래 브라우저 요청과 콜백을 연결해 값을 확인한다. 인가 서버는 등록된 리다이렉트 URI를 정해진 규칙에 맞춰 검증한다. [RFC 7636 · PKCE](https://www.rfc-editor.org/rfc/rfc7636.html) · [RFC 9700 · 보호 조치](https://www.rfc-editor.org/rfc/rfc9700.html)

리프레시 토큰은 필요한 범위와 기간으로 발급한다. 공개 클라이언트에 발급하는 경우 인가 서버는 토큰 회전이나 발신자 제약을 적용해 재사용을 탐지하거나 제한한다. [RFC 9700 · Refresh Token Protection](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14)
