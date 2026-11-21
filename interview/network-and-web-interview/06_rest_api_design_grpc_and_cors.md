# REST API Design, gRPC, and CORS

## 28. RESTful API는 어떤 제약을 따르며 어떻게 설계하나요?

**30–60초 답변**

> REST는 분산 하이퍼미디어 시스템을 위한 아키텍처 스타일입니다. 균일 인터페이스에서는 URI로 리소스를 식별하고, JSON 같은 표현으로 리소스를 조회하거나 변경합니다. HTTP 메서드·상태 코드·미디어 타입으로 메시지의 의미를 전달하고, 응답의 링크나 폼으로 클라이언트가 다음에 할 수 있는 동작을 발견하게 합니다. 예를 들어 `GET /orders/42`의 응답에 결제 링크가 있으면 클라이언트는 그 링크를 따라갈 수 있습니다. 또 클라이언트와 서버의 책임을 분리하고, 각 요청에 처리에 필요한 맥락을 담고, 응답의 캐시 가능 여부를 명시합니다. 클라이언트와 서버 사이에 프록시나 캐시를 둘 수 있는 계층 구조도 제약에 포함되며, 코드 온 디맨드는 선택 사항입니다. [Fielding, REST 아키텍처 제약](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1)

**꼬리 질문 · 무상태라면 서버에 주문이나 로그인 정보를 저장할 수 있나요?**

주문과 사용자 계정은 DB에 저장합니다. 무상태 제약은 서버가 직전 요청에 저장해 둔 클라이언트의 대화 맥락에 기대지 않고 현재 요청을 해석할 수 있어야 한다는 뜻입니다. 예를 들어 요청마다 주문 URI와 인증 토큰을 보내면 어느 API 인스턴스든 토큰을 검증하고 같은 주문을 조회할 수 있습니다. 응답의 재사용 가능 범위는 별도로 정합니다. 공개 카탈로그는 `Cache-Control: public, max-age=60`으로 공유 캐시에 60초 동안 재사용을 허용하고, 민감한 주문 응답은 `Cache-Control: no-store`로 저장을 막을 수 있습니다. [Fielding, 무상태와 캐시 제약](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_3) · [RFC 9111, HTTP 캐시 지시어](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2)

## 29. REST API와 gRPC의 차이는 무엇이며 언제 각각 선택하나요?

**30–60초 답변**

> HTTP로 구현한 REST API는 리소스와 표현을 중심으로 설계하고 표준 HTTP 메서드·상태 코드·캐시를 활용합니다. gRPC는 서비스와 원격 메서드를 중심으로 설계합니다. 기본적으로 `.proto`에 서비스와 메시지 형식을 정의하고 클라이언트 스텁과 서버 코드를 생성하며, 네이티브 gRPC는 일반적으로 HTTP/2로 Protobuf 메시지를 전송합니다. 호출은 단일 요청·응답, 서버 스트리밍, 클라이언트 스트리밍, 양방향 스트리밍을 지원합니다. 브라우저나 외부 고객이 폭넓게 호출하고 HTTP 캐시를 활용하는 공개 조회 API라면 REST를 쓰겠습니다. 팀이 양쪽 클라이언트와 서버를 관리하고 강한 타입 계약이나 스트리밍이 필요한 서비스 간 호출이라면 gRPC를 검토하겠습니다. [Fielding, REST 인터페이스](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_5) · [gRPC 핵심 개념](https://grpc.io/docs/what-is-grpc/core-concepts/) · [gRPC over HTTP/2](https://grpc.github.io/grpc/core/md_doc__p_r_o_t_o_c_o_l-_h_t_t_p2.html)

**꼬리 질문 · 브라우저에도 같은 gRPC 스트리밍을 제공할 수 있나요?**

브라우저에서 공식 gRPC-Web 클라이언트를 쓰는 경우, 일반적으로 프록시가 gRPC-Web 요청을 네이티브 gRPC로 변환합니다. 공식 구현은 단일 요청·응답과 `grpcwebtext` 모드의 서버 스트리밍을 지원합니다. 브라우저에서 서버로 지속적으로 메시지를 보내야 한다면 브라우저 구간에서 WebSocket 같은 양방향 통신을 검토하고, 내부 서비스는 gRPC로 연결할 수 있습니다. [gRPC-Web 동작 및 스트리밍 지원](https://github.com/grpc/grpc-web#streaming-support)

**꼬리 질문 · proto3 필드에서 `0`과 미전송을 어떻게 구분하나요?**

암시적 존재 여부를 쓰는 스칼라 필드는 미전송 시 숫자 `0`, 불리언 `false`, 문자열 빈 값 같은 타입 기본값으로 읽힙니다. 예를 들어 부분 갱신에서 `limit`을 그대로 둘 때와 `0`으로 바꿀 때를 구분하려면 `optional int32 limit`으로 선언하고 생성된 API에서 필드가 설정됐는지 확인합니다. [Protocol Buffers, proto3 기본값](https://protobuf.dev/programming-guides/proto3/#default) · [Protocol Buffers, 필드 존재 여부](https://protobuf.dev/programming-guides/field_presence/)

## 30. 동일 출처 정책(SOP)과 CORS는 무엇인가요?

**30–60초 답변**

> 동일 출처 정책은 브라우저가 한 출처의 스크립트에서 다른 출처의 데이터에 접근하는 범위를 제한하는 정책입니다. HTTP URL의 동일 출처는 스킴, 호스트, 포트가 모두 같을 때 성립합니다. 예를 들어 `https://app.example.com`과 `https://api.example.com`은 호스트가 달라 교차 출처입니다. CORS는 API가 `Access-Control-Allow-Origin` 같은 응답 헤더로 어느 출처의 스크립트에 응답을 공유할지 선언하는 방식입니다. 브라우저가 그 규칙을 적용하며, API는 실제 요청에서 사용자 인증과 리소스 접근 권한을 따로 검사합니다. 브라우저에서 교차 출처 요청을 전송할 수 있는 경우도 있으므로, 쿠키를 사용하는 상태 변경에는 CSRF 방어가 별도로 필요합니다. [WHATWG HTML, 출처](https://html.spec.whatwg.org/multipage/browsers.html#origins) · [WHATWG Fetch, CORS 프로토콜](https://fetch.spec.whatwg.org/#http-cors-protocol) · [OWASP, CSRF 방어](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

**꼬리 질문 · API 로그에는 `200`인데 프런트엔드의 `fetch`가 실패하면 무엇을 보나요?**

개발자 도구에서 실제 응답의 `Access-Control-Allow-Origin`이 요청의 `Origin`과 일치하는지 확인합니다. 허용 목록을 보고 출처별로 응답 헤더를 다르게 반환한다면 `Vary: Origin`을 설정해 캐시가 다른 출처의 응답을 재사용하는 일을 막습니다. 본문은 읽히는데 `X-Request-ID`만 코드에서 보이지 않으면 `Access-Control-Expose-Headers`에 그 헤더를 명시했는지 확인합니다. [WHATWG Fetch, CORS 응답 헤더와 HTTP 캐시](https://fetch.spec.whatwg.org/#cors-protocol-and-http-caches) · [WHATWG Fetch, CORS 응답 헤더](https://fetch.spec.whatwg.org/#http-responses)

## 31. CORS에서 단순 요청과 프리플라이트는 어떻게 구분하나요?

**30–60초 답변**

> 일반적인 교차 출처 `fetch`에서 `GET`, `HEAD`, `POST` 중 하나를 쓰고 코드가 추가하는 헤더의 이름과 값이 CORS 안전 목록 조건을 충족하면 브라우저는 실제 요청을 바로 보낼 수 있습니다. `Content-Type`의 허용 미디어 타입은 `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`입니다. `application/json`을 보내거나 코드에서 `Authorization` 헤더를 붙이면 프리플라이트 대상입니다. 브라우저는 캐시된 허가가 없을 때 먼저 `OPTIONS`로 예정된 메서드와 비안전 헤더 이름을 알립니다. 서버가 해당 출처·메서드·헤더를 허용해야 실제 요청을 보내고, 실제 응답도 CORS 검사를 통과해야 스크립트가 읽을 수 있습니다. [WHATWG Fetch, 안전 목록 헤더](https://fetch.spec.whatwg.org/#cors-safelisted-request-header) · [WHATWG Fetch, 프리플라이트 처리](https://fetch.spec.whatwg.org/#cors-preflight-fetch)

**꼬리 질문 · 쿠키를 포함하는 API에서 `OPTIONS`가 `401`이면 무엇을 바꾸나요?**

브라우저의 프리플라이트에는 쿠키 등 자격 증명이 실리지 않으므로, CORS 처리를 인증 미들웨어보다 먼저 적용합니다. 허용된 출처·메서드·헤더 조합에는 `204` 같은 성공 상태와 해당 `Access-Control-Allow-*` 헤더를 반환합니다. 실제 요청이 `credentials: "include"`를 쓴다면 프리플라이트와 실제 응답에 `Access-Control-Allow-Origin`으로 허용된 구체적인 출처를, `Access-Control-Allow-Credentials`로 `true`를 설정합니다. 실제 요청에서 인증과 권한을 검사하며, 브라우저가 쿠키를 보내는지는 쿠키 속성과 브라우저 정책에도 따릅니다. `Authorization`을 허용할 때는 `Access-Control-Allow-Headers`에 이름을 명시합니다. [WHATWG Fetch, CORS 요청의 자격 증명](https://fetch.spec.whatwg.org/#cors-protocol-and-credentials) · [WHATWG Fetch, 프리플라이트 처리](https://fetch.spec.whatwg.org/#cors-preflight-fetch)

**꼬리 질문 · 메서드와 헤더만 확인하면 프리플라이트 여부를 알 수 있나요?**

헤더 값의 길이와 형식도 검사합니다. 예를 들어 `Range`는 `bytes=0-499` 같은 단일 바이트 범위만 안전 목록에 들어갈 수 있습니다. 또 스트리밍 요청 본문에 `ReadableStream`을 사용하면 Fetch가 프리플라이트를 요구합니다. `Access-Control-Max-Age`는 성공한 프리플라이트 허가를 얼마나 캐시할지 지정하므로, 개발자 도구에서 `OPTIONS`가 매번 보이는지는 캐시 상태에도 좌우됩니다. [WHATWG Fetch, 안전 목록 헤더](https://fetch.spec.whatwg.org/#cors-safelisted-request-header) · [WHATWG Fetch, Request 생성과 프리플라이트](https://fetch.spec.whatwg.org/#dom-request) · [WHATWG Fetch, 프리플라이트 캐시](https://fetch.spec.whatwg.org/#cors-preflight-cache)
