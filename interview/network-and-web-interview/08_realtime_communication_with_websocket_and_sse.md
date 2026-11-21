# Real-Time Communication with WebSocket and SSE

## 42. HTTP 요청·응답과 WebSocket은 어떻게 다르며 연결은 어떻게 맺나요?

**30–60초 답변**

> HTTP에서는 클라이언트의 요청에 서버가 응답하고, 연결을 여러 요청에 재사용할 수 있습니다. WebSocket은 연결을 맺은 뒤 양쪽이 필요할 때 텍스트나 바이너리 메시지를 독립적으로 보낼 수 있어 채팅이나 공동 편집에 적합합니다. HTTP/1.1에서는 클라이언트가 `GET` 요청에 `Upgrade: websocket`, `Connection: Upgrade`, `Sec-WebSocket-Key`, `Sec-WebSocket-Version: 13`을 넣습니다. 서버가 수락하면 키로 계산한 `Sec-WebSocket-Accept`와 함께 `101 Switching Protocols`로 응답합니다. 클라이언트가 응답을 검증하면 같은 연결에서 WebSocket 프레임을 주고받습니다. `wss://`에서는 TLS 위에서 이 통신을 보호합니다. [RFC 6455, 연결 수립](https://www.rfc-editor.org/rfc/rfc6455.html#section-4) · [RFC 6455, 프레임](https://www.rfc-editor.org/rfc/rfc6455.html#section-5)

**꼬리 질문 · HTTP/2에서도 `Upgrade`와 `101`로 전환하나요?**

HTTP/2에서는 상대가 `SETTINGS_ENABLE_CONNECT_PROTOCOL=1`로 지원을 알리면, 클라이언트가 `:protocol`을 `websocket`으로 지정한 확장 `CONNECT`를 보낼 수 있습니다. 성공 응답은 `2xx`이며, WebSocket 프레임은 해당 HTTP/2 스트림에서 오갑니다. 배포할 때는 브라우저에서 로드밸런서까지의 구간과 로드밸런서에서 서버까지의 구간이 각각 어떤 연결 방식을 지원하는지 확인합니다. [RFC 8441, HTTP/2 확장 CONNECT와 WebSocket](https://www.rfc-editor.org/rfc/rfc8441.html#section-5)

## 43. WebSocket Ping/Pong과 STOMP 하트비트는 어떻게 다르나요?

**30–60초 답변**

> Ping과 Pong은 WebSocket 프로토콜의 제어 프레임입니다. 이미 Close 프레임을 받은 경우를 제외하고, Ping을 받은 쪽은 같은 페이로드를 담은 Pong으로 응답합니다. 서버는 이를 연결 상태 확인에 쓸 수 있지만, 브라우저의 `WebSocket` API는 자바스크립트에 제어 프레임을 노출하지 않습니다. STOMP는 WebSocket 위에서 사용할 수 있는 메시징 서브프로토콜로 `SEND`, `SUBSCRIBE`, `ACK` 같은 명령의 의미를 정의합니다. STOMP 하트비트는 `CONNECT`와 `CONNECTED`의 `heart-beat` 헤더로 방향별 주기를 협상하고, 보낼 STOMP 데이터가 없을 때 줄바꿈을 전송해 연결 상태를 확인합니다. [RFC 6455, Ping과 Pong](https://www.rfc-editor.org/rfc/rfc6455.html#section-5.5.2) · [WHATWG WebSockets, Ping과 Pong](https://websockets.spec.whatwg.org/#ping-and-pong-frames) · [STOMP 1.2, 하트비트](https://stomp.github.io/stomp-specification-1.2.html#Heart-beating)

**꼬리 질문 · WebSocket Pong은 오는데 STOMP 메시지가 안 오면 무엇을 보나요?**

Pong으로는 WebSocket 상대가 제어 프레임에 응답하는지 확인할 수 있습니다. STOMP에서는 `CONNECTED` 수신 여부, 대상의 구독 상태와 브로커 연결, 실제 `MESSAGE`의 도착을 각각 확인합니다. 하트비트 주기도 확인합니다. 한 방향의 송신 가능 주기가 10초이고 상대의 수신 희망 주기가 15초라면 15초를 사용합니다. 해당 방향에서 송신이나 수신 값 중 하나가 `0`이면 하트비트를 사용하지 않습니다. 정상 메시지 데이터도 연결이 살아 있다는 신호로 계산되므로 마지막 수신 바이트 시각을 기준으로 지연 허용 범위를 두고 확인합니다. [STOMP 1.2, 하트비트 협상과 수신](https://stomp.github.io/stomp-specification-1.2.html#Heart-beating)

## 44. SSE와 WebSocket은 언제 각각 선택하나요?

**30–60초 답변**

> SSE는 서버가 하나의 HTTP 응답을 열어 두고 `text/event-stream` 형식의 UTF-8 이벤트를 브라우저에 보내는 방식입니다. 서버에서 브라우저로 흐르므로 주문 상태 변경이나 알림처럼 화면에 갱신을 전달하는 기능에 적합합니다. 브라우저는 `EventSource`로 이벤트를 받고, 사용자의 주문 취소 같은 동작은 별도의 HTTP 요청으로 보낼 수 있습니다. WebSocket에서는 같은 연결을 통해 양쪽이 독립적으로 메시지를 보내며 텍스트와 바이너리를 지원합니다. 사용자 입력과 서버 갱신이 양방향으로 자주 오가는 공동 편집이라면 WebSocket을, 상태나 로그를 주로 보여 주고 사용자 명령이 드물다면 SSE를 선택하겠습니다. [WHATWG HTML, 서버 전송 이벤트](https://html.spec.whatwg.org/multipage/server-sent-events.html#server-sent-events) · [RFC 6455, WebSocket 메시지 전송](https://www.rfc-editor.org/rfc/rfc6455.html#section-6.1)

**꼬리 질문 · SSE를 외부 출처 API에 붙이고 쿠키도 보내려면 어떻게 하나요?**

`new EventSource(url, { withCredentials: true })`로 연결합니다. 서버는 허용한 구체적인 출처와 `Access-Control-Allow-Credentials: true`를 응답에 포함하고, 쿠키 전송 여부는 쿠키 속성과 브라우저 정책에도 따릅니다. 기본 `EventSource` 생성자는 URL과 `withCredentials` 옵션을 받으므로, 임의 요청 헤더가 필요한 계약이라면 `fetch`로 응답 스트림을 읽는 방법을 검토합니다. 이 경우 이벤트 해석과 재연결도 클라이언트가 구현합니다. [WHATWG HTML, EventSource 인터페이스](https://html.spec.whatwg.org/multipage/server-sent-events.html#the-eventsource-interface) · [WHATWG Fetch, CORS와 자격 증명](https://fetch.spec.whatwg.org/#cors-protocol-and-credentials)

## 45. 폴링, 롱 폴링, SSE의 차이와 연결 복구 방식은 무엇인가요?

**30–60초 답변**

> 폴링은 클라이언트가 일정 주기마다 조회하므로 구현이 단순하지만, 변화가 없어도 요청하고 갱신 지연이 조회 주기에 따라 달라집니다. 롱 폴링은 서버가 변화나 대기 기한까지 요청을 열어 두고 응답하면 클라이언트가 다음 요청을 보냅니다. SSE는 하나의 열린 응답에서 여러 이벤트를 연속해서 받습니다. 브라우저의 `EventSource`는 복구 가능한 연결 종료 시 재연결하고, 마지막 이벤트 ID가 있으면 `Last-Event-ID`를 보냅니다. 누락분을 복구하려면 서버가 이벤트를 보관하고 이 ID 뒤에 발생한 이벤트를 재전송해야 합니다. [RFC 6202, HTTP 롱 폴링과 스트리밍](https://www.rfc-editor.org/rfc/rfc6202.html#section-2) · [WHATWG HTML, EventSource 재연결과 Last-Event-ID](https://html.spec.whatwg.org/multipage/server-sent-events.html#last-event-id)

**꼬리 질문 · 재연결이 다른 서버 인스턴스로 가거나 이벤트 보관 기한을 넘기면요?**

이벤트마다 스트림 안에서 순서를 찾을 수 있는 `id`를 붙이고, 어느 인스턴스에서나 조회할 수 있는 로그에 기록합니다. 서버는 `Last-Event-ID` 이후를 재생하고, 클라이언트는 이벤트 ID로 중복 적용을 막습니다. 보관 범위 밖의 ID로 재연결했으면 현재 상태와 그 시점의 커서를 다시 읽도록 안내합니다. 브라우저는 `CONNECTING`에서 연결을 열면 `OPEN`이 되고, 재연결할 때는 다시 `CONNECTING`이 됩니다. 서버의 `retry` 필드는 재연결 대기 시간을 밀리초로 지정할 수 있습니다. 사용자가 화면을 떠나면 `close()`로 종료하고, 서버에서 재연결을 중단시키려면 연결 요청에 `204 No Content`로 응답할 수 있습니다. [WHATWG HTML, EventSource 처리 모델](https://html.spec.whatwg.org/multipage/server-sent-events.html#processing-model) · [WHATWG HTML, 이벤트 스트림 해석](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation)

**꼬리 질문 · 서버는 이벤트를 보냈는데 브라우저에서 한꺼번에 보이면요?**

이벤트가 빈 줄로 끝나는지, 애플리케이션이 이벤트 단위로 데이터를 내보내는지 먼저 확인합니다. 서버에 직접 연결했을 때는 바로 보인다면 프록시 버퍼링을 점검합니다. 예를 들어 NGINX에서는 SSE 경로에 `proxy_buffering off`를 적용할 수 있습니다. 유휴 타임아웃으로 스트림이 끊기는 경우에는 타임아웃보다 짧은 주기로 SSE 주석을 보내고 각 구간에서 수신 시각을 확인합니다. [WHATWG HTML, SSE 작성 시 고려 사항](https://html.spec.whatwg.org/multipage/server-sent-events.html#authoring-notes) · [NGINX, proxy_buffering](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)
