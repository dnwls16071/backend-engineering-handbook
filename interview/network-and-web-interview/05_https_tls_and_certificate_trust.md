# HTTPS, TLS, and Certificate Trust

## 22. HTTP와 HTTPS의 차이는 무엇인가?

**30–60초 답변**

> HTTPS는 HTTP 통신에 TLS 보호를 적용한 방식입니다. `https://`로 접속하면 클라이언트는 인증서 검증 등을 통해 접속 대상 서버를 인증합니다. 이후 HTTP 헤더와 본문을 암호화해 전송 구간에서 기밀성을 지키고, 인증 태그를 검증해 변조를 확인합니다. 메서드와 상태 코드의 의미는 동일합니다. 예를 들어 평문 HTTP로 로그인하면 중간에서 요청을 읽을 수 있지만, HTTPS에서는 TLS 연결 양 끝의 애플리케이션이 복호화한 데이터를 읽습니다. HTTP/3는 QUIC에 TLS 1.3을 통합해 같은 보안 목적을 달성합니다. [RFC 9110 §4.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.2) · [RFC 8446 §1](https://www.rfc-editor.org/rfc/rfc8446.html#section-1) · [RFC 9001 §3](https://www.rfc-editor.org/rfc/rfc9001.html#section-3)

**꼬리 질문 · 로드밸런서에서 TLS를 종료하면 어디까지 암호화되나요?**

클라이언트의 TLS 연결은 로드밸런서까지입니다. 로드밸런서가 백엔드로 요청을 보낼 때 HTTPS를 쓰면 그 구간에 별도의 TLS 연결이 생기고, 평문 HTTP를 쓰면 그 구간의 요청은 평문으로 전송됩니다. [RFC 9110 §3.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-3.7) · [RFC 9110 §4.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.2.2)

## 23. TLS 1.3 핸드셰이크는 어떻게 진행되는가?

**30–60초 답변**

> TCP 위의 일반적인 TLS 1.3 연결에서는 클라이언트가 `ClientHello`로 지원 버전과 암호 스위트, 임시 ECDHE 공개 키를 보냅니다. 서버는 `ServerHello`로 선택한 버전과 암호 스위트, 자체 공개 키를 보냅니다. 양쪽은 각자의 임시 개인 키와 상대 공개 키로 같은 공유 비밀을 계산하고 핸드셰이크 키를 유도합니다. `ServerHello` 이후 서버의 `EncryptedExtensions`, `Certificate`, `CertificateVerify`, `Finished`는 핸드셰이크 키로 보호됩니다. 클라이언트는 인증서와 서버 서명, `Finished`를 확인한 뒤 자기 `Finished`를 보냅니다. 각 방향에서 보낸 `Finished` 다음의 일반 애플리케이션 데이터에는 해당 방향의 애플리케이션 트래픽 키를 사용합니다. [RFC 8446 §2](https://www.rfc-editor.org/rfc/rfc8446.html#section-2) · [RFC 8446 §4.4](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4) · [RFC 8446 §7](https://www.rfc-editor.org/rfc/rfc8446.html#section-7)

**꼬리 질문 · 세션을 재개할 때도 인증서부터 다시 받나요?**

서버가 이전 연결에서 발급한 티켓에 대응하는 사전 공유 키(PSK)를 받아들이면 그 키를 기반으로 새 연결을 인증해 서버 인증서와 `CertificateVerify`를 생략합니다. 새 ECDHE 키 교환을 함께 사용할 수 있습니다. 재개 시 선택할 수 있는 0-RTT 데이터는 재생 공격으로 중복 처리될 수 있어, 주문 생성처럼 중복 실행의 영향이 큰 요청은 핸드셰이크를 마친 뒤 보냅니다. [RFC 8446 §2.2–3](https://www.rfc-editor.org/rfc/rfc8446.html#section-2.2) · [RFC 8470 §3](https://www.rfc-editor.org/rfc/rfc8470.html#section-3)

## 24. 서버 인증서는 어떻게 신뢰하며 키 교환과는 어떤 관계가 있는가?

**30–60초 답변**

> 서버 인증서는 서버 이름과 공개 키를 연결합니다. 클라이언트는 서버 인증서와 중간 인증서들의 발급자 서명을 따라가며, 자신의 신뢰 저장소에 있는 루트까지 유효한 경로가 이어지는지 확인합니다. 인증서의 유효기간과 용도 제약을 검사하고, 접속한 호스트 이름이 인증서의 `Subject Alternative Name`과 일치하는지도 확인합니다. TLS 1.3에서 서버는 인증서에 대응하는 개인 키로 핸드셰이크 기록에 `CertificateVerify` 서명을 만들어 키를 보유했음을 증명합니다. ECDHE는 양쪽이 공유 비밀을 계산하는 역할을 하고, 여기서 통신 방향별 대칭 트래픽 키를 유도합니다. [RFC 5280 §6](https://www.rfc-editor.org/rfc/rfc5280.html#section-6) · [RFC 9525 §6](https://www.rfc-editor.org/rfc/rfc9525.html#section-6) · [RFC 8446 §4.4.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.3) · [RFC 8446 §7.1](https://www.rfc-editor.org/rfc/rfc8446.html#section-7.1)

**꼬리 질문 · 같은 주소가 한 기기에서만 인증서 오류를 내면 무엇을 확인하나요?**

먼저 기기의 시간, 접속 호스트 이름, 기기가 신뢰하는 루트를 확인합니다. 서버가 필요한 중간 인증서를 보내는지도 봅니다. 한 기기는 이전에 확보한 중간 인증서로 경로를 만들고 다른 기기는 경로를 완성하지 못할 수 있습니다. [RFC 5280 §6.1](https://www.rfc-editor.org/rfc/rfc5280.html#section-6.1) · [RFC 8446 §4.4.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.2)

## 25. 대칭 키와 비대칭 키는 어떻게 다르며 TLS에서는 어디에 쓰이는가?

**30–60초 답변**

> 대칭 키 암호화에서는 한 방향의 데이터를 보내는 쪽과 받는 쪽이 같은 비밀 키로 암호화하고 복호화합니다. 비대칭 암호 기술은 공개 키와 개인 키 쌍을 사용합니다. 예를 들어 서버가 개인 키로 서명하면 클라이언트는 대응하는 공개 키로 서명을 검증할 수 있습니다. TLS 1.3은 인증서 기반 연결에서 이 서명으로 서버를 인증하고, ECDHE 키 교환으로 공유 비밀을 합의합니다. 이후 HTTP 데이터는 유도한 대칭 키와 AES-GCM 같은 인증 암호화 방식으로 효율적으로 보호합니다. [NIST · Digital Signature](https://csrc.nist.gov/glossary/term/digital_signature) · [RFC 8446 §2](https://www.rfc-editor.org/rfc/rfc8446.html#section-2) · [RFC 8446 §5.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-5.2)

**꼬리 질문 · 서버 인증서의 개인 키가 나중에 유출되면 과거 통신도 복호화되나요?**

매 연결에서 임시 ECDHE 키를 만들고 사용 후 삭제했으며 그 키와 트래픽 키가 유출되지 않았다면, 나중에 인증서의 개인 키만 유출돼도 기록된 과거 통신에서 트래픽 키를 다시 계산할 수 없습니다. 이를 순방향 비밀성(forward secrecy)이라고 합니다. [RFC 8446 부록 E.1](https://www.rfc-editor.org/rfc/rfc8446.html#appendix-E.1)

## 26. 공인 인증기관은 무엇이며 Let’s Encrypt는 상용 CA와 어떻게 다른가?

**30–60초 답변**

> 공인 인증기관(CA)은 도메인 제어권 등 인증서에 들어갈 정보를 검증하고 인증서에 서명합니다. 브라우저는 자신이 신뢰하는 루트까지 인증서 경로를 검증합니다. Let’s Encrypt도 공인 CA이며, 도메인 검증(DV) 인증서를 무료로 발급합니다. ACME 클라이언트가 HTTP 경로나 DNS 레코드로 도메인 제어권을 증명하면 발급과 갱신을 자동화할 수 있습니다. DigiCert 같은 상용 CA도 ACME를 지원하며 조직 신원 확인을 포함하는 OV나 EV도 제공합니다. DV, OV, EV는 인증서가 증명하는 정보의 범위를 나타냅니다. 데이터 암호화 방식은 TLS 핸드셰이크에서 협상합니다. [Let’s Encrypt · FAQ](https://letsencrypt.org/docs/faq/) · [Let’s Encrypt · How It Works](https://letsencrypt.org/how-it-works/) · [RFC 8555 §1](https://www.rfc-editor.org/rfc/rfc8555.html#section-1) · [CA/Browser Forum · TLS Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/) · [DigiCert · ACME Automation](https://docs.digicert.com/en/certcentral/automate-certificate-lifecycle/automate-certificate-issuance-using-acme.html) · [RFC 8446 §2](https://www.rfc-editor.org/rfc/rfc8446.html#section-2)

**꼬리 질문 · Let’s Encrypt에서 `*.example.com` 인증서를 자동으로 갱신하려면요?**

와일드카드 발급·갱신에는 `DNS-01`을 사용할 수 있습니다. ACME 클라이언트가 DNS 제공업체 API로 검증용 `_acme-challenge.example.com` TXT 레코드를 등록하게 하고, 갱신한 인증서가 실제 TLS 종료 지점에 반영됐는지 확인합니다. [Let’s Encrypt · Challenge Types](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)
