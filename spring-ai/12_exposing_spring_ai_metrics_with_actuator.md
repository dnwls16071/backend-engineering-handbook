# Exposing Spring AI Metrics with Actuator

Spring AI는 채팅 모델 호출을 Micrometer Observation으로 기록한다. Spring Boot Actuator가 수집된 메트릭을 보여 주고 Prometheus 레지스트리가 스크레이프 형식으로 내보낸다. 실습은 Spring Boot 4.1.0과 Spring AI 2.0.2를 기준으로 한다. [Spring AI Observability](https://docs.spring.io/spring-ai/reference/2.0/observability/index.html) · [Spring Boot Actuator Metrics](https://docs.spring.io/spring-boot/4.1/reference/actuator/metrics.html)

## 1. 레지스트리와 엔드포인트 설정

[채팅 API 프로젝트](04_building_chat_apis_with_openai_and_ollama.md)의 `build.gradle`에서 `dependencies`에 다음 두 항목을 추가한다.

```groovy
implementation 'org.springframework.boot:spring-boot-starter-actuator'
runtimeOnly 'io.micrometer:micrometer-registry-prometheus'
```

`src/main/resources/application-monitoring.properties`를 추가한다. 모델 호출과 HTTP 요청의 분위수를 Prometheus에서 구할 수 있도록 각각 히스토그램을 활성화한다.

```properties
management.endpoints.web.exposure.include=health,metrics,prometheus
management.metrics.distribution.percentiles-histogram.gen_ai.client.operation=true
management.metrics.distribution.percentiles-histogram.http.server.requests=true
spring.ai.chat.observations.log-prompt=false
spring.ai.chat.observations.log-completion=false
```

프로파일을 활성화한 뒤 [요청 예제](11_measuring_llm_cost_latency_errors_and_quality.md)를 한 번 이상 실행한다. 모델이 토큰 사용량을 응답에 포함해야 사용량 메트릭을 확인할 수 있다.

```bash
./gradlew bootRun --args='--spring.profiles.active=openai,monitoring'
```

```bash
curl -fsS http://localhost:8080/actuator/health
curl -fsS http://localhost:8080/actuator/metrics/gen_ai.client.operation
curl -fsS http://localhost:8080/actuator/metrics/gen_ai.client.token.usage
curl -fsS http://localhost:8080/actuator/prometheus \
  | rg '^gen_ai_client_(operation_seconds_(count|sum|bucket)|token_usage_total)'
```

## 2. Prometheus에 전달되는 이름

| Actuator 이름 | Prometheus 시계열 | 용도 |
| --- | --- | --- |
| `gen_ai.client.operation` | `gen_ai_client_operation_seconds_count`, `_sum`, `_bucket` | 모델 호출 횟수, 총 시간, 분위수 |
| `gen_ai.client.token.usage` | `gen_ai_client_token_usage_total` | 토큰 유형별 누적 사용량 |
| `http.server.requests` | `http_server_requests_seconds_count`, `_bucket` | 사용자 HTTP 요청 건수와 응답 시간 |

채팅 호출은 `gen_ai_operation_name="chat"`으로 좁힌다. 토큰 유형 `input`과 `output`으로 비용을 각각 계산하고, 한 번에 합계만 보고 싶으면 `total`만 사용한다. 모델 실제 응답 ID나 대화 ID처럼 값이 요청마다 달라지는 항목은 메트릭 태그로 만들지 않는다. 운영 환경에서는 관리 엔드포인트를 수집기와 운영자가 접근하는 네트워크에 둔다. [Spring Boot Actuator Endpoints](https://docs.spring.io/spring-boot/4.1/reference/actuator/endpoints.html)
