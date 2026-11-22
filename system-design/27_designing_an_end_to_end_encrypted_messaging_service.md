# Designing an End-to-End Encrypted Messaging Service

종단간 암호화 메신저는 암호화된 메시지를 전달하는 서버와 평문을 읽을 수 있는 단말의 책임을 나눈다. 16번 일반 채팅 흐름에 기기 단위 세션, 오프라인 전달과 재등록의 조건을 추가한다. [Signal Sesame](https://signal.org/docs/specifications/sesame/) · [Signal Double Ratchet](https://signal.org/docs/specifications/doubleratchet/) · [RFC 6455 WebSocket](https://www.rfc-editor.org/rfc/rfc6455.html)

## 1. 사용자와 기기의 식별자를 분리한다

공개 프로토콜의 세션 관리 모델에 따라 단말에서 수신 기기에 대한 암호화 세션을 사용한다. 서버는 기기 목록과 전달 상태 및 필요한 암호문을 관리하고, 새 기기 등록과 해지 시 어떤 기기에 이후 메시지를 보낼지 검증한다. [Signal Sesame](https://signal.org/docs/specifications/sesame/)

## 2. 온라인·오프라인 전달과 확인을 구분한다

온라인 단말에는 실시간 연결로 암호문을 보낸다. 오프라인 단말의 경우 기기별 대기 항목과 보존 기한을 둔다. 송신 수락, 해당 기기의 수신 ACK, 사용자 읽음은 별도 상태이며, 재전달은 메시지 ID로 중복 표시를 막는다. [Signal Sesame](https://signal.org/docs/specifications/sesame/) · [RFC 6455 WebSocket](https://www.rfc-editor.org/rfc/rfc6455.html) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 3. 기기 변경과 순서가 바뀐 메시지를 시험한다

기기 추가·해지 직후, 오프라인 복귀, 메시지 중복과 순서 역전을 테스트한다. 메시지 복호화는 공개 프로토콜의 검증된 구현이 담당하도록 하고, 서버 지표는 대기·실패·연결 단위의 상태를 중심으로 설계한다. [Signal Sesame](https://signal.org/docs/specifications/sesame/) · [Signal Double Ratchet](https://signal.org/docs/specifications/doubleratchet/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
