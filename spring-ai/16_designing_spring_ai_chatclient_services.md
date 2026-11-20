# Designing Spring AI ChatClient Services

`JdbcTemplate`이 JDBC의 반복 작업을 공통화하고 `RestClient`가 HTTP 요청 구성을 담당하듯, `ChatClient`는 메시지·옵션·어드바이저를 구성해 `ChatModel`을 호출한다. 애플리케이션 서비스는 이 API 위에 출력 계약, 정책, 실패 처리를 정의한다. [Spring Framework · REST Clients](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html) · [Spring AI · Chat Client](https://docs.spring.io/spring-ai/reference/2.0/api/chatclient.html)

## 1. 요청 체인과 애플리케이션 경계

```text
Controller → ChatService → ChatClient → Advisors → ChatModel → Provider
```

| 위치 | 책임 |
| --- | --- |
| Controller | 인증된 요청을 받고 일반 응답과 SSE의 HTTP 계약을 정의한다. |
| ChatService | 입력 범위, 시스템 지시, 모델 옵션, 출력 검증과 애플리케이션 오류를 관리한다. |
| Provider 설정 | 모델 ID, 키, 타임아웃과 환경별 교체를 담당한다. |

`prompt()`는 요청을 구성한다. `call().content()`는 완성된 텍스트를 읽고 `stream().content()`는 `Flux<String>`으로 조각을 소비한다. 중간에 오류가 나거나 사용자가 연결을 끊을 수 있는 스트림은 이미 전송한 부분과 최종 성공 상태를 서비스에서 구별한다. [Spring AI · Chat Client](https://docs.spring.io/spring-ai/reference/2.0/api/chatclient.html)

## 2. 환경 설정과 모델 옵션

OpenAI 키는 `OPENAI_API_KEY` 환경 변수로 애플리케이션에 전달하고 브라우저와 Git에 두지 않는다. Docker Compose를 쓸 때도 키는 실행 환경에서 주입한다. 모델 ID, 프롬프트 버전, 온도는 실험 결과에 함께 기록한다. 온도 지원 범위와 사용 가능 여부는 모델마다 확인하며, 낮은 온도에서도 동일 응답을 전제로 테스트하지 않는다. [Spring AI · OpenAI Chat](https://docs.spring.io/spring-ai/reference/2.0/api/chat/openai-chat.html)

실습에서는 같은 질문으로 일반 응답과 스트리밍을 비교한다. 첫 조각까지 걸린 시간, 전체 응답 시간, 연결 종료 후 완료 여부를 기록한다. `ChatService`에 대한 단위 테스트는 빈 응답, 변환 실패, 타임아웃이 애플리케이션 계약에 맞게 처리되는지 확인한다.

관련 문서 [Spring AI Core Components](03_spring_ai_core_components.md) · [Building Chat APIs with OpenAI and Ollama](04_building_chat_apis_with_openai_and_ollama.md)
