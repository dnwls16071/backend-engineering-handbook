# HTTP Headers, Content Negotiation, and Cookies

HTTP 헤더는 표현의 형식, 클라이언트의 선호, 메시지 전송 방식, 인증과 상태 관리에 필요한 정보를 전달한다. `Content-Type`처럼 콘텐츠를 해석하는 데 쓰이는 필드와 `Transfer-Encoding`처럼 HTTP/1.1 메시지 전송을 기술하는 필드는 역할이 다르다.

## 1. 표현과 콘텐츠 관련 헤더

서버는 같은 자원을 JSON, HTML, 여러 언어 또는 여러 압축 방식의 표현으로 제공할 수 있다. 표현은 데이터와 그 해석을 돕는 메타데이터로 구성된다.

| 필드 | 역할 | 예 |
| --- | --- | --- |
| `Content-Type` | 미디어 타입과 관련 매개변수를 알린다. | `text/html; charset=UTF-8` |
| `Content-Encoding` | 표현에 적용된 콘텐츠 코딩을 알린다. | `gzip` |
| `Content-Language` | 표현이 대상으로 하는 사용자 언어를 나타낸다. | `ko` |
| `Content-Length` | 일반적인 콘텐츠 전송에서 옥텟 수를 알린다. | `15` |

`Content-Length`를 쓸 때는 문자 수 대신 인코딩된 바이트 수를 사용한다. 본문이 압축되어 전송되면 해당 콘텐츠의 압축된 바이트 수를 센다. `HEAD`와 `304`처럼 콘텐츠가 없는 응답에도 제한된 조건에서 해당 표현의 길이를 메타데이터로 실을 수 있다.

## 2. 콘텐츠 협상

클라이언트는 `Accept`로 미디어 타입, `Accept-Language`로 언어, `Accept-Encoding`으로 콘텐츠 코딩에 대한 선호를 표현한다. `Accept-Charset`은 UTF-8이 널리 사용되면서 사용이 권장되지 않는 필드다. `q` 값은 `0`부터 `1`까지이며 생략하면 `1`이다. `q=0`은 해당 선택지를 수용하지 않는다는 뜻이다. 선택 과정에서는 매체 범위의 구체성도 고려한다.

```http
GET /announcements HTTP/1.1
Host: example.com
Accept: text/html, application/json;q=0.8
Accept-Language: ko, en;q=0.7
Accept-Encoding: gzip

```

서버가 한국어 HTML을 선택하면 `Content-Type: text/html; charset=UTF-8`과 `Content-Language: ko`를 응답에 포함할 수 있다. 언어와 미디어 타입에 따라 응답을 고를 때는 `Vary: Accept-Language, Accept`로 선택에 사용한 요청 필드를 캐시에 알릴 수 있다. 압축 표현도 `Accept-Encoding`에 따라 선택한다면 이를 `Vary`에 포함한다.

## 3. 길이, 압축, 청크, 범위

| 방식 | 관련 필드 | 메시지를 읽는 기준 |
| --- | --- | --- |
| 길이를 아는 전송 | `Content-Length` | 정해진 바이트 수를 읽는다. |
| 압축된 표현 | `Content-Encoding: gzip` | 응답의 콘텐츠 코딩에 맞춰 압축을 푼다. |
| HTTP/1.1 청크 전송 | `Transfer-Encoding: chunked` | 각 청크의 16진수 길이를 읽고 길이 `0`인 청크에서 끝을 확인한다. |
| 부분 전송 | 요청의 `Range`, 응답의 `Content-Range` | `206 Partial Content`에서 받은 바이트 구간과 전체 길이를 확인한다. |

HTTP/1.1 송신자는 `Transfer-Encoding`이 있는 메시지에 `Content-Length`를 함께 보내면 안 된다. `Range: bytes=0-1023` 요청을 처리한 서버가 앞 1,024바이트를 보내면 `Content-Range: bytes 0-1023/8192`처럼 구간과 전체 길이를 알릴 수 있다.

## 4. 요청 맥락, 상태, 인증

| 필드 | 읽을 수 있는 정보 |
| --- | --- |
| `Host` | HTTP/1.1의 대상 호스트와 필요한 경우 포트 |
| `Referer` | 요청이 시작된 문서의 주소 정보. 브라우저 정책에 따라 줄이거나 생략할 수 있다. |
| `User-Agent`, `From` | 사용자 에이전트 정보와 선택적으로 제공하는 담당자의 이메일 주소 |
| `Server`, `Date` | 응답을 생성한 서버 소프트웨어 정보와 메시지 생성 시각 |
| `Location` | 생성된 자원이나 리다이렉트의 대상 URI |
| `Allow`, `Retry-After` | 현재 허용되는 메서드와 다시 요청하기까지 기다릴 시간 또는 시각 |
| `Authorization`, `WWW-Authenticate` | 클라이언트 자격 증명과 서버가 제시하는 인증 과제 |

## 5. 쿠키와 요청 상태

서버가 `Set-Cookie`를 보내면 브라우저가 쿠키를 저장할 수 있다. 브라우저는 도메인, 경로, 만료 시각, 요청 맥락에 맞는 후속 요청에 `Cookie`를 넣는다. 로그인 상태는 예를 들어 쿠키가 전달한 세션 식별자를 서버 측 세션과 연결해 복원한다.

```http
Set-Cookie: session_id=example123; Max-Age=1800; Path=/; Secure; HttpOnly; SameSite=Lax
```

| 속성 | 효과 |
| --- | --- |
| `Max-Age`, `Expires` | 만료 시간을 정한다. 둘이 함께 있으면 `Max-Age`가 우선한다. |
| `Domain`, `Path` | 어떤 호스트와 경로의 요청에 보낼지 제한한다. `Domain`을 생략한 쿠키는 설정한 호스트에만 전송된다. |
| `Secure` | 보안 연결에서만 전송하도록 제한한다. |
| `HttpOnly` | `document.cookie` 같은 스크립트 API에서 쿠키를 읽을 수 없게 한다. 브라우저는 조건에 맞는 HTTP 요청에 쿠키를 계속 포함한다. |
| `SameSite` | 교차 사이트 요청에서 쿠키가 전송되는 조건을 제어한다. `Lax`는 일반적으로 안전한 메서드의 최상위 탐색을 허용하며 `None`에는 `Secure`가 필요하다. |

`SameSite`는 사이트 기준으로 동작하며 `Domain`은 쿠키의 호스트 범위를 정한다. `HttpOnly`는 스크립트가 쿠키 값을 직접 읽는 경로를 제한한다.
