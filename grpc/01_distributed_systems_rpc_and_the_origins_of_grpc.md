# Distributed Systems, RPC, and the Origins of gRPC

서비스를 여러 프로세스와 서버로 나누면 각 부분을 독립적으로 배포하고 확장할 수 있다. 그만큼 네트워크 호출, 부분 장애, 서비스 간 계약 변경을 다루는 일이 늘어난다. gRPC는 이 환경에서 서비스 간 호출의 계약과 통신 방식을 표준화하는 데 쓰인다.

## 1. 통신 프로토콜이 다양해진 이유

전송해야 하는 데이터, 메시지를 먼저 보낼 쪽, 연결을 유지할 시간, 사용할 클라이언트와 인프라가 다르면 프로토콜에 필요한 기능도 달라진다.

| 사용 상황 | 주로 고려할 방식 | 선택 이유 |
| --- | --- | --- |
| 브라우저나 외부 파트너에 리소스 API 제공 | HTTP API와 JSON | HTTP 메서드, 상태 코드, 캐시를 활용할 수 있고 브라우저와 범용 HTTP 도구에서 다루기 쉽다. |
| 채팅처럼 클라이언트와 서버가 수시로 메시지 발신 | WebSocket | 연결을 유지하면서 양쪽이 독립적으로 메시지를 보낼 수 있다. |
| 여러 언어로 만든 내부 서비스 사이에서 메서드 호출 | gRPC | 서비스와 메시지 타입을 하나의 계약으로 정의할 수 있고 요청·응답과 스트리밍을 지원한다. |

API 설계 방식, 메시지 인코딩, 전송 규칙은 서로 다른 층이다. REST는 아키텍처 스타일이고 RPC는 원격 메서드 호출 방식이다. HTTP/2는 HTTP 메시지를 전송하는 프로토콜이고 Protocol Buffers는 메시지 정의와 직렬화에 쓰인다. 같은 HTTP/2 위에서도 JSON을 주고받는 HTTP API와 Protobuf를 쓰는 gRPC가 모두 가능하다.

**공식 문서** [HTTP 의미론](https://www.rfc-editor.org/rfc/rfc9110.html) · [HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html) · [WebSocket](https://www.rfc-editor.org/rfc/rfc6455.html) · [Protocol Buffers 개요](https://protobuf.dev/overview/)

## 2. 분산 시스템의 문제와 RPC 패러다임

| 문제 | 호출에서 드러나는 모습 | 설계에서 결정할 사항 |
| --- | --- | --- |
| 네트워크 지연 | 직렬로 이어진 호출마다 전송과 대기 시간이 추가된다. 여러 응답을 기다리면 가장 느린 응답에 전체 시간이 좌우될 수 있다. | 호출마다 기다릴 시간과 장애 시 반환할 결과를 정한다. |
| 부분 장애 | 호출한 서비스는 살아 있지만 백엔드나 중간 네트워크가 응답하지 않는다. | 정상 응답을 기다릴 한도와 실패를 어디까지 전달할지 정한다. |
| 실행 결과 불확실성 | 서버는 쓰기를 완료했지만 응답이 유실되거나 늦어서 클라이언트가 실패로 본다. | 재시도 가능한 오류를 좁히고, 상태 변경은 요청 식별자로 중복 처리를 막거나 결과를 조회할 수 있게 한다. |
| 계약과 상태 변화 | 배포 시점이 다른 서버와 클라이언트가 같은 계약을 해석해야 하고, 여러 시스템의 데이터 변경이 따로 완료될 수 있다. | 스키마의 호환성을 유지하고, 서비스 경계를 넘는 상태 변경과 복구 방법을 별도로 설계한다. |

RPC는 원격 서비스의 연산을 `GetStock` 같은 메서드로 표현한다. 클라이언트는 스텁을 호출하고, 스텁과 런타임이 요청을 직렬화해 보낸다. 서버는 요청을 해석해 핸들러를 실행하고 결과와 상태를 돌려준다. 호출 문법은 로컬 메서드와 비슷하지만 실행과 응답 수신은 각각 실패할 수 있다.

예를 들어 `ReserveStock` 호출에서 재고 예약을 저장한 직후 응답이 늦으면 클라이언트는 `DEADLINE_EXCEEDED`를 받을 수 있다. 같은 예약 요청을 다시 보내야 한다면 동일한 요청 식별자를 사용하고, 서버가 이미 처리한 요청의 결과를 재사용할 수 있게 설계한다. gRPC는 기본적으로 deadline을 설정하지 않으므로 호출 목적에 맞게 지정하고, 재시도가 필요한 경우 횟수와 백오프를 정한다.

**공식 문서** [gRPC 호출 수명과 종료](https://grpc.io/docs/what-is-grpc/core-concepts/#rpc-life-cycle) · [Deadline](https://grpc.io/docs/guides/deadlines/) · [Retry](https://grpc.io/docs/guides/retry/) · [상태 코드](https://grpc.io/docs/guides/status-codes/)

## 3. Google이 gRPC를 만든 배경

Google은 데이터센터 안과 데이터센터 사이의 서비스 통신에 범용 RPC 인프라인 Stubby를 운영했다. 공통 인프라를 사용하면 효율, 보안, 신뢰성 개선을 여러 서비스에 적용할 수 있었다. Google은 이 경험을 바탕으로 HTTP/2 공개 표준을 사용하는 gRPC를 설계하고 2015년에 오픈소스로 공개했다. 이 구조를 통해 여러 언어와 플랫폼에서 같은 호출 계약을 사용할 수 있게 했다.

- **HTTP/2 전송** · 한 연결에서 여러 요청을 독립적인 스트림으로 진행할 수 있다. 스트림과 연결의 흐름 제어, 헤더 압축도 사용할 수 있다.
- **Protocol Buffers 계약** · gRPC의 기본 방식에서는 `.proto`에 서비스 메서드와 메시지를 정의한다. 언어별 코드 생성 플러그인으로 클라이언트 스텁과 서버 측 인터페이스를 만든다.
- **호출 유형** · 요청과 응답이 하나씩인 unary 외에도 서버 스트리밍, 클라이언트 스트리밍, 양방향 스트리밍을 지원한다. 스트리밍은 한 호출이 진행되는 동안 여러 메시지를 전달할 때 사용한다.

아래는 요청과 응답이 하나씩인 재고 조회 계약 예시다. 서비스의 공개 계약을 정의하며, 응답의 필드 번호는 직렬화된 메시지에서 필드를 식별한다.

```proto
syntax = "proto3";

package inventory.v1;

service InventoryService {
  rpc GetStock(GetStockRequest) returns (GetStockResponse);
}

message GetStockRequest {
  string sku = 1;
}

message GetStockResponse {
  int32 available_quantity = 1;
}
```

같은 계약으로 배포 시점이 다른 프로그램을 연결하려면 사용 중인 필드 번호를 바꾸지 않는다. 필드를 삭제하면 해당 번호를 예약해 재사용을 막는다. 브라우저가 주 클라이언트라면 HTTP API와 gRPC-Web의 연동 비용도 비교한다.

**공식 문서** [gRPC 설계 동기와 원칙](https://grpc.io/blog/principles/) · [Google의 gRPC 공개 발표](https://opensource.googleblog.com/2015/02/introducing-grpc-new-open-source-http2.html) · [gRPC 서비스 정의와 스트리밍](https://grpc.io/docs/what-is-grpc/core-concepts/) · [Proto3 스키마 변경 규칙](https://protobuf.dev/programming-guides/proto3/#updating) · [gRPC-Web](https://grpc.io/docs/platforms/web/basics/)
