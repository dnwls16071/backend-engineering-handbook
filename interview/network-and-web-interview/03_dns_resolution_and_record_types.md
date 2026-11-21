# DNS Resolution and Record Types

## 12. `www.naver.com`의 IP 주소를 DNS로 어떻게 찾나요?

**30–60초 답변**

> 브라우저나 운영체제가 사용할 수 있는 DNS 캐시를 먼저 확인하고, 필요한 답이 없으면 설정된 재귀 리졸버에 주소를 질의합니다. 재귀 리졸버도 답을 캐시하고 있을 수 있고, 필요한 위임 정보까지 없다면 루트 서버에 질의해 `.com`을 담당하는 서버를 안내받습니다. `.com` 서버에서는 `naver.com`을 담당하는 권한 서버를 안내받고, 그 서버에 `www.naver.com`의 주소 레코드를 묻습니다. 응답이 `CNAME` 별칭이면 대상 이름을 계속 해석해 `A` 또는 `AAAA` 레코드를 얻습니다. 리졸버는 응답 레코드를 각 TTL에 맞춰 캐시하고 클라이언트에 돌려줍니다. [RFC 1034 DNS 조회와 캐시](https://www.rfc-editor.org/rfc/rfc1034) · [RFC 9499 DNS 용어](https://www.rfc-editor.org/rfc/rfc9499) · [RFC 3596 IPv6 주소 레코드](https://www.rfc-editor.org/rfc/rfc3596)

**꼬리 질문 · DNS 레코드를 바꿨는데 일부 사용자에게 이전 주소가 보이는 이유는 무엇인가요?**

이미 이전 레코드를 받은 재귀 리졸버는 그 레코드의 남은 TTL 동안 캐시에서 응답할 수 있습니다. 권한 서버의 응답과 영향을 받는 사용자의 리졸버 응답을 비교해 값과 남은 TTL을 확인합니다. 전환 전에 TTL을 낮출 때는 낮추기 전에 저장된 캐시가 만료될 시간을 고려하고, 별칭을 사용한다면 `CNAME`과 대상 주소의 TTL도 각각 확인합니다. [RFC 1034 DNS 조회와 캐시](https://www.rfc-editor.org/rfc/rfc1034)

## 13. DNS는 UDP와 TCP를 언제 사용하나요?

**30–60초 답변**

> 전통적인 DNS의 일반 질의는 53번 포트의 UDP로 보내는 경우가 많고, 별도 연결 설정 없이 작은 요청과 응답을 주고받을 수 있습니다. 기본 DNS의 UDP 메시지 한도는 512바이트이며, EDNS를 사용하면 질의자가 수신할 수 있는 더 큰 UDP 페이로드 크기를 알릴 수 있습니다. 응답을 허용 크기에 담을 수 없어 서버가 `TC` 플래그를 설정하면 클라이언트는 같은 질의를 TCP로 다시 보내며, 처음부터 TCP를 선택할 수도 있습니다. 영역 전체 전송인 AXFR은 TCP로 수행합니다. 암호화된 DNS 전송에는 TLS 위의 DoT와 HTTPS 위의 DoH가 있습니다. [RFC 1035 DNS 메시지 전송](https://www.rfc-editor.org/rfc/rfc1035) · [RFC 6891 EDNS](https://www.rfc-editor.org/rfc/rfc6891) · [RFC 7766 DNS over TCP](https://www.rfc-editor.org/rfc/rfc7766) · [RFC 5936 AXFR](https://www.rfc-editor.org/rfc/rfc5936) · [RFC 7858 DoT](https://www.rfc-editor.org/rfc/rfc7858) · [RFC 8484 DoH](https://www.rfc-editor.org/rfc/rfc8484)

**꼬리 질문 · 작은 DNS 응답은 오는데 큰 응답만 실패하면 어떻게 확인하나요?**

같은 이름과 레코드 유형을 같은 리졸버에 UDP와 TCP로 각각 질의해 결과를 비교합니다. UDP 응답에 `TC`가 있는데 TCP 질의가 실패하면 해당 경로의 TCP 53 연결을 확인합니다. UDP 응답이 아예 없고 TCP는 성공한다면 EDNS로 광고한 크기와 경로의 MTU, 조각난 IP 패킷의 손실 가능성을 확인합니다. [RFC 6891 EDNS](https://www.rfc-editor.org/rfc/rfc6891) · [RFC 7766 DNS over TCP](https://www.rfc-editor.org/rfc/rfc7766)

## 14. DNS 서버의 역할과 `A`, `CNAME`, `TXT` 레코드를 설명해 주세요.

**30–60초 답변**

> 재귀 리졸버는 클라이언트 대신 답을 찾거나 캐시된 답을 반환합니다. 루트 서버와 최상위 도메인(TLD) 서버는 각자 담당하는 영역에서 다음 권한 서버로 위임을 안내하고, 질의한 이름의 영역을 맡은 권한 서버는 그 영역의 데이터를 바탕으로 응답합니다. `A`는 IPv4 주소, `AAAA`는 IPv6 주소, `CNAME`은 별칭의 대상 이름을 담습니다. `TXT`는 문자열을 담으며 발신 메일의 SPF 정책처럼 별도 규격에서 의미를 정해 사용합니다. 서버 역할을 나누면 영역마다 독립적으로 데이터를 운영할 수 있고, 레코드 유형을 나누면 클라이언트가 필요한 데이터만 질의할 수 있습니다. [RFC 9499 DNS 용어](https://www.rfc-editor.org/rfc/rfc9499) · [RFC 1034 DNS 구조와 CNAME](https://www.rfc-editor.org/rfc/rfc1034) · [RFC 1035 A와 TXT 레코드](https://www.rfc-editor.org/rfc/rfc1035) · [RFC 3596 AAAA 레코드](https://www.rfc-editor.org/rfc/rfc3596) · [RFC 7208 SPF](https://www.rfc-editor.org/rfc/rfc7208)

**꼬리 질문 · `example.com`처럼 영역의 최상단 이름을 표준 `CNAME`으로 지정할 수 있나요?**

영역 최상단에는 영역의 기본 정보인 `SOA`와 권한 서버를 지정하는 `NS`가 필요합니다. 표준 `CNAME`은 같은 이름의 `SOA`, `NS` 또는 주소 레코드와 함께 둘 수 없으므로, 최상단에 주소를 제공할 때는 `A`와 필요에 따라 `AAAA`를 둡니다. [RFC 1034 DNS 영역과 CNAME](https://www.rfc-editor.org/rfc/rfc1034) · [RFC 2181 CNAME 제약](https://www.rfc-editor.org/rfc/rfc2181)
