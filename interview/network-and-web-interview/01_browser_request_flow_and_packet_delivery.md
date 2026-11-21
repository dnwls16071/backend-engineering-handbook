# Browser Request Flow and Packet Delivery

## 1. 브라우저에서 `www.google.com`에 접속하면 어떤 일이 일어나나요?

**30–60초 답변**

> `https://www.google.com/`로 이동한다고 가정하면, 브라우저는 URL을 해석하고 재사용할 수 있는 HTTP 캐시 응답이 있으면 그 응답을 사용합니다. 네트워크 요청이 필요하고 기존 연결도 재사용할 수 없다면 DNS 캐시나 조회를 통해 접속할 IP 주소를 얻습니다. 새 연결에서 HTTP/2를 사용하는 예라면 TCP 연결을 맺고, TLS 핸드셰이크에서 인증서의 신뢰성과 호스트 이름을 검증하며 암호화 키와 HTTP 버전을 협상합니다. 브라우저는 `GET /`를 전송하고 응답으로 받은 HTML을 파싱하면서 CSS·JavaScript·이미지 같은 리소스를 가져옵니다. HTML과 CSS로 DOM과 CSSOM을 구성한 뒤 화면에 그릴 요소의 위치와 크기를 계산하고 페인트와 합성을 거쳐 표시합니다. [RFC 9111 HTTP 캐싱](https://www.rfc-editor.org/rfc/rfc9111) · [RFC 1034 DNS](https://www.rfc-editor.org/rfc/rfc1034) · [RFC 8446 TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446) · [RFC 9525 TLS 서비스 식별](https://www.rfc-editor.org/rfc/rfc9525) · [RFC 9113 HTTP/2](https://www.rfc-editor.org/rfc/rfc9113) · [web.dev 렌더링 경로](https://web.dev/articles/critical-rendering-path)

**꼬리 질문 · 실제 요청이 어느 단계에서 지연되는지 어떻게 확인하나요?**

Chrome 개발자 도구의 Network에서 문서 요청의 Timing을 열어 DNS 조회, 초기 연결과 TLS, 첫 바이트 대기, 응답 다운로드 시간을 확인합니다. 캐시 적중이나 연결 재사용으로 건너뛴 단계도 확인하고, Protocol 열에서 실제로 사용한 HTTP 버전을 봅니다. 예를 들어 `h3`라면 UDP 위의 QUIC이 연결 설정 과정에 TLS 1.3을 통합한 경로입니다. [Chrome DevTools Network 가이드](https://developer.chrome.com/docs/devtools/network/reference) · [RFC 9000 QUIC](https://www.rfc-editor.org/rfc/rfc9000) · [RFC 9114 HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)

## 2. 웹 요청이 패킷으로 전달되는 과정을 설명해 주세요.

**30–60초 답변**

> Ethernet을 사용하는 호스트가 외부 서버에 HTTP/2 요청을 보내는 상황에서, TCP 연결과 TLS 핸드셰이크에 쓰이는 패킷도 IP 라우팅을 따라 전달됩니다. 연결이 준비되면 TLS가 HTTP/2 요청 데이터를 암호화하고, TCP가 그 바이트를 세그먼트로 나눠 IP 패킷에 싣습니다. 호스트는 라우팅 테이블로 다음 홉을 정하고, MAC 주소가 캐시에 없으면 IPv4는 ARP, IPv6는 이웃 탐색(NDP)으로 다음 홉의 MAC 주소를 구해 Ethernet 프레임을 보냅니다. 라우터는 링크 헤더를 벗겨 목적지 IP를 조회하고, TTL이나 Hop Limit을 줄인 뒤 다음 링크에 맞춰 다시 캡슐화합니다. 수신 측은 TCP로 바이트를 순서대로 전달하고, TLS에서 복호화와 무결성 검증을 거쳐 HTTP 요청을 처리합니다. [RFC 9293 TCP](https://www.rfc-editor.org/rfc/rfc9293) · [RFC 8446 TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446) · [RFC 826 ARP](https://www.rfc-editor.org/rfc/rfc826) · [RFC 4861 IPv6 이웃 탐색](https://www.rfc-editor.org/rfc/rfc4861) · [RFC 1812 IPv4 라우터](https://www.rfc-editor.org/rfc/rfc1812) · [RFC 8200 IPv6](https://www.rfc-editor.org/rfc/rfc8200)

**꼬리 질문 · 내 PC에서 캡처한 첫 요청 프레임의 목적지 MAC은 누구의 주소인가요?**

외부 서버로 가는 경로가 기본 게이트웨이를 가리키면, PC의 Ethernet 캡처에서 프레임의 목적지 MAC은 기본 게이트웨이 주소이고 내부 IP 패킷의 목적지 주소는 원격 서버 IP입니다. 목적지가 같은 링크에 있으면 호스트는 목적지 장치의 MAC 주소를 사용합니다. 이 차이로 링크에서 프레임을 받는 장치와 IP 패킷의 최종 목적지를 구분할 수 있습니다. [RFC 826 ARP](https://www.rfc-editor.org/rfc/rfc826) · [RFC 4861 IPv6 이웃 탐색](https://www.rfc-editor.org/rfc/rfc4861)
