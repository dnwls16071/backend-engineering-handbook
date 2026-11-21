# Authentication, Sessions, JWT, and OAuth

## 33. HTTP는 무상태인데 로그인 상태는 어떻게 유지하나요?

**30–60초 답변**

> HTTP가 무상태라는 말은 요청을 해석하는 데 이전 요청에 대한 프로토콜 상태가 필요하지 않다는 뜻입니다. 애플리케이션은 로그인에 성공하면 브라우저에 세션 ID를 쿠키로 전달할 수 있습니다. 브라우저가 후속 요청에 그 쿠키를 붙이면 서버는 세션 저장소에서 사용자와 만료 정보를 찾습니다. API에 액세스 토큰을 보내는 방식에서는 요청마다 토큰을 검증하고 허용된 작업을 판단합니다. 어느 쪽이든 각 요청에는 서버가 요청을 사용자나 권한과 연결할 정보가 들어갑니다. [RFC 9110의 HTTP 의미론](https://www.rfc-editor.org/rfc/rfc9110.html#section-3.3) · [OWASP 세션 관리](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

**꼬리 질문 · 다음 요청이 다른 앱 서버에 도착하면 어떻게 하나요?**

서버 세션 방식에서는 각 인스턴스가 같은 세션 저장소를 조회하도록 구성할 수 있습니다. 사용자 활동에 따른 만료 갱신과 로그아웃 무효화가 어느 인스턴스에서 처리해도 일관되게 반영되는지 확인합니다. 요청을 같은 인스턴스로 보내는 세션 고정 방식을 쓴다면 인스턴스 교체나 장애 때 로그인 상태를 어떻게 이어갈지도 설명해야 합니다. [OWASP 세션 저장과 만료](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

## 34. 인증과 인가는 어떻게 다른가요?

**30–60초 답변**

> 인증은 요청 주체가 누구인지 확인하는 과정이고, 인가는 그 주체가 특정 리소스에 특정 작업을 할 수 있는지 판단하는 과정입니다. 예를 들어 로그인 세션이 유효하면 주문을 요청한 사용자를 확인할 수 있습니다. 그 후 사용자가 주문 소유자인지, 관리자에게 해당 업무 권한이 있는지 서버가 검사합니다. 인증에 성공했더라도 주문마다 필요한 권한을 확인해야 합니다. [OWASP 인가 설계](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

**꼬리 질문 · `401`과 `403`은 언제 반환하나요?**

유효한 인증 정보가 없어 API가 `401 Unauthorized`를 반환한다면, 응답에 그 리소스에 적용할 `WWW-Authenticate` 챌린지를 하나 이상 포함합니다. 서버가 요청을 이해했어도 주어진 권한으로 작업을 허용할 수 없으면 `403 Forbidden`을 반환할 수 있습니다. 서버는 접근이 금지된 리소스의 존재를 숨기는 정책에서 `404 Not Found`를 사용할 수도 있습니다. [RFC 9110의 401](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.2) · [RFC 9110의 403](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.4) · [RFC 6750의 Bearer 오류 응답](https://www.rfc-editor.org/rfc/rfc6750.html#section-3.1)

## 35. 쿠키와 세션은 인증에서 어떻게 동작하고, 보안상 무엇을 고려하나요?

**30–60초 답변**

> 쿠키는 브라우저가 저장하고, 범위와 조건이 맞는 요청에 자동으로 보내는 데이터입니다. 서버 세션은 사용자 정보와 인증 상태를 서버가 보관하고, 브라우저에는 보통 그 세션을 찾는 데 필요한 임의의 ID만 둡니다. 세션 ID가 유출되면 만료나 폐기 전까지 다른 요청에서 사용될 수 있으므로 서버에서 만료와 무효화를 적용합니다. 쿠키에 `Secure`를 설정해 HTTPS로 전송하고, `HttpOnly`로 스크립트의 직접 읽기를 제한하며, `SameSite`와 필요한 CSRF 방어로 교차 사이트 요청을 관리합니다. [OWASP 세션 관리](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) · [OWASP CSRF 방어](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

**꼬리 질문 · 로그인 성공 시 세션 ID를 바꾸는 이유는 무엇인가요?**

인증 전에 사용하던 ID가 알려졌더라도 그 ID로 인증된 세션을 사용할 수 없도록, 로그인이나 권한 상승 직후 ID를 재발급하고 이전 ID를 무효화합니다. `HttpOnly`가 있어도 페이지에서 실행되는 스크립트는 브라우저를 통해 인증 요청을 보낼 수 있으므로, 스크립트 삽입을 막는 방어도 필요합니다. [OWASP 세션 ID 재발급과 쿠키 속성](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

## 36. JWT는 어떤 구조이고, 액세스 토큰과 리프레시 토큰을 왜 나누나요?

**30–60초 답변**

> 일반적인 서명된 JWT는 Base64url로 인코딩한 헤더, 클레임을 담은 페이로드, 서명을 점으로 연결한 형태입니다. 페이로드는 인코딩되어 있으므로 읽을 수 있고, 서명은 내용의 무결성과 발급 주체를 확인하는 데 씁니다. 액세스 토큰은 보호된 API 호출에 쓰므로 수명을 짧게 제한할 수 있습니다. 리프레시 토큰은 인가 서버에서 새 액세스 토큰을 발급받을 때만 사용하며, 더 오래 보관할 수 있는 만큼 갱신과 폐기를 관리합니다. 두 토큰의 역할은 형식과 독립적이어서, 액세스 토큰이나 리프레시 토큰에는 서버가 조회하는 불투명한 값을 사용할 수도 있습니다. [RFC 7519의 JWT 구조](https://www.rfc-editor.org/rfc/rfc7519.html#section-3) · [RFC 6749 §1.4와 §1.5](https://www.rfc-editor.org/rfc/rfc6749.html#section-1.4)

**꼬리 질문 · API 서버는 서명만 확인하면 되나요?**

신뢰하는 발급자의 키와 허용 알고리즘으로 서명을 확인하고, `iss`로 발급자, `aud`로 대상 API, `exp`와 `nbf`로 시간 조건을 검증합니다. 이후 API가 요구하는 권한 범위와 리소스 접근 조건을 확인합니다. 예를 들어 Spring Security의 JWT 리소스 서버에서는 `issuer-uri`로 발급자를 지정하고 대상 API 검증에는 `audiences` 또는 별도 검증기를 추가할 수 있습니다. [RFC 8725의 JWT 검증 권고](https://www.rfc-editor.org/rfc/rfc8725.html#section-3) · [Spring Security 6.5 JWT 검증](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/jwt.html)

## 37. JWT가 탈취됐을 때 어떻게 대응하고, 탈취 여부는 어떻게 판단하나요?

**30–60초 답변**

> 일반적인 Bearer 액세스 토큰은 소지자가 토큰이 허용하는 작업을 요청할 수 있어서, 유효한 서명만으로는 요청 주체가 바뀌었는지 알기 어렵습니다. 유출이 의심되면 영향 계정이나 인가 부여 범위를 찾아 해당 세션과 리프레시 토큰을 폐기합니다. API가 서명과 만료를 로컬에서만 검사하면 이미 발급된 액세스 토큰은 만료까지 통과할 수 있습니다. 즉시 차단이 필요하면 API가 폐기 목록을 확인하게 하거나 토큰 활성 상태를 조회하는 구조를 사용합니다. 리프레시 토큰 회전 중 이미 사용한 토큰이 다시 들어오는 현상과 비정상 접근 이력을 조사하되, 재요청이나 네트워크 변경도 가능하므로 신호 하나로 탈취를 단정하기는 어렵습니다. [RFC 6750의 Bearer 토큰 모델](https://www.rfc-editor.org/rfc/rfc6750.html) · [RFC 9700 §4.14의 리프레시 토큰 보호](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14) · [RFC 7009의 토큰 폐기](https://www.rfc-editor.org/rfc/rfc7009.html#section-3) · [RFC 7662의 토큰 상태 조회](https://www.rfc-editor.org/rfc/rfc7662.html#section-2)

**꼬리 질문 · 사고 조사 로그에는 무엇을 남기나요?**

토큰 원문 대신 요청 ID, 발급자, 검증된 토큰 식별자나 운영용 상관관계 ID, 시간, 결과와 호출 위치를 남깁니다. 같은 인증 정보의 짧은 시간 내 상이한 사용 패턴, 회전된 리프레시 토큰의 재사용, 계정 조작 이력을 함께 확인합니다. 개별 토큰 유출과 발급용 서명 키 유출은 영향 범위가 달라 별도로 조사합니다. [OWASP 로깅에서 제외할 데이터](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude) · [RFC 9700의 리프레시 토큰 회전](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14.2)

## 38. 리프레시 토큰을 서버에 저장하면 서버 세션과 무엇이 다른가요?

**30–60초 답변**

> 둘 다 서버 상태를 유지할 수 있습니다. 서버 세션 방식에서는 일반 API 요청을 인증할 때 세션 ID로 저장된 사용자 상태를 조회합니다. 자체 검증 가능한 JWT 액세스 토큰과 서버 관리 리프레시 토큰을 쓰면, 일반 API 요청은 서명과 클레임으로 검증하고 토큰 갱신 시에 인가 서버가 저장된 토큰 상태를 확인합니다. 조회가 일어나는 위치와 빈도가 달라집니다. 세션은 저장소에서 폐기한 뒤 조회 시점에 반영되고, 리프레시 토큰 폐기는 이후 갱신을 차단합니다. 이미 발급한 액세스 토큰의 즉시 폐기까지 요구하면 별도의 상태 확인이 필요합니다. [RFC 6749 §1.5의 갱신 흐름](https://www.rfc-editor.org/rfc/rfc6749.html#section-1.5) · [RFC 7009의 폐기 설계 고려 사항](https://www.rfc-editor.org/rfc/rfc7009.html#section-3)

**꼬리 질문 · 로그아웃 버튼에서 클라이언트의 토큰만 지우면 되나요?**

그 기기에서 인증 정보를 더 이상 제출하지 않게 할 수 있습니다. 다른 곳에 남은 복사본이나 갱신 권한도 끊어야 한다면 서버 세션이나 리프레시 토큰을 서버에서 무효화합니다. API의 즉시 차단 기준과 액세스 토큰 만료까지 허용하는 시간을 서비스 요구에 맞춰 정합니다. [OWASP 세션 무효화](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) · [RFC 7009의 토큰 폐기](https://www.rfc-editor.org/rfc/rfc7009.html#section-2)

## 39. OAuth 2.0은 어떻게 동작하나요?

**30–60초 답변**

> OAuth 2.0은 클라이언트가 보호된 리소스에 제한된 권한으로 접근하도록 하는 인가 프레임워크입니다. 예를 들어 일정 앱이 사용자의 캘린더 읽기 권한을 요청합니다. 인가 코드 흐름에서 앱은 브라우저를 인가 서버로 보내고, 인가 서버는 사용자를 확인하고 필요한 경우 동의를 받은 뒤 등록된 리디렉션 URI로 인가 코드를 전달합니다. 앱은 토큰 엔드포인트에서 코드와 PKCE 검증값을 제출해 액세스 토큰을 받고, 리소스 서버에 그 토큰으로 요청합니다. 리소스 서버는 토큰의 유효성과 권한 범위를 확인합니다. [RFC 6749의 역할과 인가 코드 흐름](https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1) · [RFC 7636의 PKCE 흐름](https://www.rfc-editor.org/rfc/rfc7636.html#section-4) · [RFC 9700의 권고](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.1.1)

**꼬리 질문 · `state`와 PKCE는 각각 무엇을 확인하나요?**

`state`는 콜백을 클라이언트가 시작한 브라우저 요청과 연결하는 데 사용할 수 있습니다. PKCE는 요청마다 새로 만든 검증값을 바탕으로 `S256` 챌린지를 먼저 보내고, 코드 교환 시 그 검증값을 확인해 인가 코드와 교환 주체를 연결합니다. 기밀 클라이언트라면 토큰 요청에서 등록된 클라이언트 인증 방식도 적용합니다. [RFC 6749 §10.12의 요청 바인딩](https://www.rfc-editor.org/rfc/rfc6749.html#section-10.12) · [RFC 7636의 검증값과 챌린지](https://www.rfc-editor.org/rfc/rfc7636.html#section-4)

## 40. SSO는 어떤 구조로 동작하며 OAuth 2.0과는 어떤 관계인가요?

**30–60초 답변**

> SSO는 하나의 로그인 경험으로 여러 앱을 이용하는 구조입니다. 예를 들어 앱 A가 인증을 위해 브라우저를 공통 ID 제공자에 보내면, 제공자는 로그인 뒤 자체 세션을 유지합니다. 이후 앱 B에서도 같은 제공자로 이동할 때 그 세션이 유효하면, 정책이 허용하는 경우 자격 증명을 다시 입력하지 않고 앱 B로 돌아올 수 있습니다. OpenID Connect는 OAuth 2.0 흐름에 로그인 확인용 ID 토큰을 추가하고, 각 앱은 ID 토큰의 서명, 발급자, 수신 대상과 만료를 확인하고, 요청에 `nonce`를 넣었다면 그 값도 대조한 뒤 앱 자체의 세션을 만들 수 있습니다. OAuth 액세스 토큰은 API 접근용으로 사용하고, 로그인 주체는 OIDC의 ID 토큰과 검증 규칙을 따릅니다. [OpenID Connect Core의 개요와 인가 코드 흐름](https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth) · [OpenID Connect ID 토큰 검증](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation)

**꼬리 질문 · 앱 A에서 로그아웃하면 앱 B에서도 로그아웃되나요?**

앱 A의 로컬 세션, 앱 B의 로컬 세션, ID 제공자의 세션은 서로 다른 범위에 있습니다. 앱 A가 자기 세션만 종료하면 앱 B의 기존 세션은 계속 유효할 수 있습니다. 공통 로그아웃이 요구되면 제공자 세션 종료와 다른 앱으로의 로그아웃 전파를 지원하는지 확인하고, 앱마다 세션 정리까지 검증합니다. [OpenID Connect RP-Initiated Logout](https://openid.net/specs/openid-connect-rpinitiated-1_0.html) · [OpenID Connect Back-Channel Logout](https://openid.net/specs/openid-connect-backchannel-1_0.html)
