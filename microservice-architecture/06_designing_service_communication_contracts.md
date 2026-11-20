# Designing Service Communication Contracts

서비스 통신 방식은 어떤 답을 언제 받아야 하는지와 실패를 어떻게 해석할지로 결정한다. 동기 호출은 응답을 기다리는 시간 동안 호출자가 의존하고, 비동기 흐름은 접수와 완료를 별도 상태로 표현할 수 있다. 동기·비동기의 업무 의미와 프로토콜의 스트리밍 방식은 따로 판단한다. [Microservice communication patterns](https://microservices.io/patterns/)

## REST, GraphQL, gRPC, WebSocket

| 방식 | 잘 맞는 계약 | 운영할 항목 |
| --- | --- | --- |
| HTTP REST | 주문 리소스 생성·조회, 상태 코드와 표현이 분명한 요청 | 멱등 키, 캐시 가능 여부, 오류 응답, 호환 변경 |
| GraphQL | 화면에서 필요한 필드를 선택하는 조회 | 필드 권한, 깊이·비용, 데이터 로딩 배치와 부분 오류 |
| gRPC | 스키마 기반 내부 RPC, 단일 요청·응답 또는 스트리밍 | 스키마 진화, deadline, 상태 코드 |
| WebSocket | 연결을 유지한 채 주문 상태를 양방향 전달 | 재연결, 세션 권한, 느린 소비자, 재접속 후 상태 복구 |

REST는 HTTP의 메서드·상태 의미를 활용한다. GraphQL은 쿼리 문법과 실행 모델을 정의하고, WebSocket은 메시지를 전달할 수 있는 연결을 제공한다. gRPC 스트림의 존재와 도메인 이벤트의 영속 전달은 서로 다른 선택이다. [HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) · [GraphQL Specification](https://spec.graphql.org/) · [gRPC Core Concepts](https://grpc.io/docs/what-is-grpc/core-concepts/) · [WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455.html)

## 주문 사례의 포트 설계

주문 조회 입력 포트는 주문 ID를 받아 정해진 정보를 반환한다. 같은 기능을 REST나 gRPC로 공개할 때 DTO, 상태 코드, 메타데이터는 각 어댑터에서 변환한다. 여러 조회를 GraphQL로 조합할 때도 필드 권한과 집계 비용을 경계에서 검사한다. 상태 푸시는 새 정보가 있다는 신호로 쓰고, 재연결 시 현재 상태를 조회할 수 있게 한다.

재고 예약은 응답을 못 받았다고 해서 실행되지 않았다고 단정할 수 없다. 계약에 예약 키, 결과 확인 경로, deadline, 재시도 가능 여부를 명시한다. 프로토콜 타입과 HTTP 클라이언트 예외는 포트 경계에서 업무 결과로 변환한다. 재고 확정까지 기다릴 수 없는 흐름은 [비동기 메시징](08_reliable_asynchronous_messaging_between_services.md)으로 접수·처리를 나눌 수 있다. [gRPC Deadlines](https://grpc.io/docs/guides/deadlines/)
