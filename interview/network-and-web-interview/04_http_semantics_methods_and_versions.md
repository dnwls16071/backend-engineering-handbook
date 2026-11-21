# HTTP Semantics, Methods, and Versions

## 1. HTTP는 무엇이고 요청과 응답은 어떻게 오가는가?

**30–60초 답변**

> HTTP는 클라이언트와 서버가 리소스를 조회하거나 처리할 때 사용하는 애플리케이션 계층 프로토콜입니다. 클라이언트는 메서드로 의도한 작업을, 요청 대상으로 그 작업을 적용할 리소스를 지정합니다. 요청에는 헤더와 필요에 따른 본문도 담을 수 있습니다. 서버는 요청을 받아 상태 코드, 헤더, 필요한 경우 본문을 반환합니다. 예를 들어 `GET /products/42`에 `200 OK`를 받으면 응답 본문의 JSON에서 상품 정보를, `Content-Type`에서 본문의 형식을 확인할 수 있습니다. [RFC 9110 §3.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-3.4) · [RFC 9110 §6](https://www.rfc-editor.org/rfc/rfc9110.html#section-6)

**꼬리 질문 · 요청 한 번에 응답이 여러 개 올 수 있나요?**

중간 상태를 알리는 `1xx` 응답이 먼저 올 수 있고, 일반적인 요청 처리는 최종 응답 하나로 끝납니다. 예를 들어 `100 Continue`는 클라이언트가 요청 본문을 계속 보내도 된다는 신호입니다. [RFC 9110 §15.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.2)

## 2. HTTP의 비지속 연결과 무상태성은 어떻게 다른가?

**30–60초 답변**

> 비지속 연결은 요청과 응답을 한 번 교환한 뒤 연결을 닫는 방식입니다. 초기 HTTP/1.0에서는 이 방식이 일반적이었고, HTTP/1.1부터는 연결을 유지해 후속 요청에 재사용하는 것이 기본입니다. 무상태성은 각 요청의 의미를 이전 메시지에 의존하지 않고 해석할 수 있다는 HTTP의 성질입니다. 로그인 서비스는 요청마다 쿠키로 세션 ID를 받아 저장된 로그인 상태를 찾을 수 있습니다. 이 방식은 TCP 연결을 재사용할 때도, 새 연결을 열 때도 동작합니다. [RFC 1945 §1.3](https://www.rfc-editor.org/rfc/rfc1945.html#section-1.3) · [RFC 9112 §9.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-9.3) · [RFC 9110 §3.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-3.3) · [RFC 6265 §4](https://www.rfc-editor.org/rfc/rfc6265.html#section-4)

**꼬리 질문 · 로드밸런서가 다음 요청을 다른 인스턴스로 보내도 로그인 상태가 유지되나요?**

두 인스턴스가 같은 세션 저장소를 사용하면 어느 쪽이든 쿠키의 세션 ID로 로그인 상태를 찾을 수 있습니다. 인스턴스별 메모리에 세션을 두었다면 다음 요청을 세션이 있는 인스턴스로 보내거나 세션 정보를 공유해야 합니다.

## 3. HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/3의 차이는 무엇인가?

**30–60초 답변**

> HTTP 버전은 메서드와 상태 코드의 의미를 공유하고, 메시지를 연결에서 주고받는 방식이 달라집니다. HTTP/1.0은 보통 응답 후에 연결을 닫았고, HTTP/1.1은 지속 연결을 기본으로 사용합니다. HTTP/1.1에서 요청을 파이프라이닝해도 응답은 요청 순서대로 전송됩니다. HTTP/2는 TCP 연결 하나에서 여러 스트림의 바이너리 프레임을 섞어 보내고 HPACK으로 헤더를 압축합니다. TCP에서 손실이 발생하면 같은 연결의 여러 스트림이 재전송을 기다릴 수 있습니다. HTTP/3는 UDP 위의 QUIC 스트림으로 각 요청을 전송하고 QPACK으로 헤더를 압축합니다. 손실 때문에 한 스트림의 데이터가 늦어져도 다른 스트림의 수신 데이터는 전달할 수 있습니다. [RFC 1945 §1.3](https://www.rfc-editor.org/rfc/rfc1945.html#section-1.3) · [RFC 9112 §9.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-9.3) · [RFC 9113 §2](https://www.rfc-editor.org/rfc/rfc9113.html#section-2) · [RFC 9114 §2](https://www.rfc-editor.org/rfc/rfc9114.html#section-2) · [RFC 9114 §4.2.1](https://www.rfc-editor.org/rfc/rfc9114.html#section-4.2.1)

**꼬리 질문 · HTTP/2에서 손실 하나가 다른 요청에도 왜 영향을 주나요?**

여러 HTTP 스트림이 TCP 바이트 흐름 하나를 공유합니다. 중간 바이트가 유실되면 TCP는 그 뒤에 먼저 도착한 바이트를 애플리케이션에 넘기기 전에 누락된 바이트를 기다립니다. QUIC은 스트림별로 순서를 보장하고, 연결의 혼잡 제어는 여전히 공유합니다. [RFC 9113 §1](https://www.rfc-editor.org/rfc/rfc9113.html#section-1) · [RFC 9114 §2](https://www.rfc-editor.org/rfc/rfc9114.html#section-2)

## 4. GET, POST, PUT, PATCH는 각각 언제 사용하는가?

**30–60초 답변**

> `GET`은 리소스의 표현을 조회하는 안전하고 멱등한 메서드입니다. `GET` 요청 본문에는 일반적으로 정의된 의미가 없어서 조회 조건은 보통 쿼리 문자열에 넣습니다. `POST`는 요청 본문을 대상 리소스의 규칙에 따라 처리해 달라는 뜻으로, 주문 생성이나 결제 요청에 쓸 수 있습니다. `PUT`은 지정한 URI의 리소스를 요청 본문으로 생성하거나 그 상태를 교체할 때 쓰며 멱등합니다. `PATCH`는 본문에 담긴 변경 사항을 적용할 때 씁니다. 네 메서드 중 안전한 메서드는 `GET`이고, `POST`와 `PATCH`의 멱등성은 API 구현에 달려 있습니다. 예를 들어 같은 값으로 설정하는 `PATCH`는 멱등하게 만들 수 있습니다. [RFC 9110 §9.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2) · [RFC 9110 §9.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3) · [RFC 5789 §2](https://www.rfc-editor.org/rfc/rfc5789.html#section-2)

**꼬리 질문 · 메서드에 따라 응답을 캐시할 수 있나요?**

`GET` 응답은 상태 코드와 캐시 지시어 등 조건에 따라 저장하고 재사용할 수 있습니다. `POST`와 `PATCH`도 응답에 명시적인 신선도 정보가 있고 `Content-Location`이 요청 대상 URI와 같으면 캐시 조건을 충족할 수 있습니다. 이렇게 저장한 응답은 이후 `GET`이나 `HEAD` 요청에 쓸 수 있습니다. `PUT` 응답은 캐시할 수 없습니다. [RFC 9111 §3](https://www.rfc-editor.org/rfc/rfc9111.html#section-3) · [RFC 9110 §9.3.3–4](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.3) · [RFC 5789 §2](https://www.rfc-editor.org/rfc/rfc5789.html#section-2)

## 5. HTTP 메서드의 멱등성이란 무엇이며 재시도와 어떤 관련이 있는가?

**30–60초 답변**

> 멱등성이란 동일한 요청을 여러 번 적용했을 때 클라이언트가 의도한 서버 측 효과가 한 번 적용했을 때와 같다는 뜻입니다. `DELETE /orders/42`는 첫 요청에 `204`, 두 번째 요청에 `404`를 반환해도 주문이 삭제된 상태라는 효과는 같습니다. 응답 코드와 요청 로그는 달라질 수 있습니다. 연결이 끊겨 응답을 받지 못하면 멱등한 요청은 첫 시도가 적용됐을 가능성을 감안해 재시도할 수 있습니다. `POST`처럼 기본적으로 멱등성이 보장되지 않는 요청은 작업이 적용되지 않았음을 확인하거나 API가 중복 처리를 막는다고 명시한 경우에 자동 재시도를 고려합니다. [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)

**꼬리 질문 · 주문 생성 요청에서 타임아웃이 나면 중복을 어떻게 막나요?**

클라이언트가 주문 의도마다 고유한 멱등성 키를 생성하고 같은 주문을 재시도할 때 다시 보냅니다. 서버는 주문 생성과 해당 키의 처리 기록을 한 트랜잭션으로 저장하고, 동일한 키와 내용이 다시 오면 이미 만든 주문을 반환하도록 설계합니다.
