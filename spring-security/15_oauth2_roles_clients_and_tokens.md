# OAuth 2.0 Roles, Client Types, and Tokens

## 1. 역할을 호출 경로에 대입하기

카탈로그 포털이 사용자 대신 카탈로그 API를 조회한다고 가정한다. 포털은 인가 서버에서 접근 권한을 얻고 발급받은 액세스 토큰을 API에 전달한다. [RFC 6749 · OAuth 2.0 Roles](https://www.rfc-editor.org/rfc/rfc6749.html#section-1.1)

| 역할 | 카탈로그 예 |
| --- | --- |
| 리소스 소유자 | 접근을 승인하는 사용자 |
| 클라이언트 | 사용자를 대신해 API를 호출하는 카탈로그 포털 |
| 인가 서버 | 권한 부여를 처리하고 토큰을 발급하는 서버 |
| 리소스 서버 | 토큰을 검증하고 카탈로그 API 접근을 결정하는 서버 |

`client_id`는 클라이언트 등록을 식별한다. 기밀 클라이언트는 서버 등 통제된 환경에서 자격 증명을 보관할 수 있다. 공개 클라이언트에는 브라우저 코드나 배포된 네이티브 앱처럼 공유 비밀을 보호할 수 없는 환경이 포함된다. 서버측 웹 애플리케이션과 브라우저에서만 실행되는 앱은 배포 위치에 따라 클라이언트 유형이 달라질 수 있다. [RFC 6749 · Client Types](https://www.rfc-editor.org/rfc/rfc6749.html#section-2.1)

## 2. 권한 범위와 발급 결과

| 값 | 쓰이는 곳 |
| --- | --- |
| 인가 코드 | 클라이언트가 토큰 엔드포인트에서 권한 부여 결과를 교환한다. |
| 액세스 토큰 | 리소스 서버에 접근 권한을 제시한다. |
| 리프레시 토큰 | 인가 서버에서 새 액세스 토큰을 요청한다. |
| ID 토큰 | [OpenID Connect 클라이언트](17_openid_connect_and_id_tokens.md)가 로그인 결과를 확인한다. |

`scope`는 `catalog.read`처럼 요청하거나 부여한 권한 범위다. 실제로 부여된 범위는 클라이언트가 요청한 것과 다를 수 있다. 액세스 토큰은 JWT나 불투명 문자열일 수 있다. Bearer 토큰은 소지한 주체가 사용할 수 있으므로 HTTPS로 전달하고 요청 로그에서 제외한다. [RFC 6749 · Access Token Scope](https://www.rfc-editor.org/rfc/rfc6749.html#section-3.3) · [RFC 6750 · Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750.html)
