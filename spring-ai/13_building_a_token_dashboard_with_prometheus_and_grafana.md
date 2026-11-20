# Building a Token Dashboard with Prometheus and Grafana

Spring Boot 앱이 모델 호출 지표를 노출하면 Prometheus가 주기적으로 읽고 Grafana가 그래프로 보여 준다. Docker Compose에서 Prometheus는 `app:8080`, Grafana는 `prometheus:9090`으로 연결된다. 호스트에서는 루프백으로 테스트 API와 대시보드를 연다. [Docker Compose Networking](https://docs.docker.com/compose/how-tos/networking/) · [Grafana Prometheus 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/)

## 1. Compose와 Prometheus 설정

[Actuator 설정](12_exposing_spring_ai_metrics_with_actuator.md)을 적용한 채팅 프로젝트의 `build.gradle`에 다음 항목을 추가한다.

```groovy
tasks.named('bootJar') {
    archiveFileName = 'observability-lab.jar'
}
```

프로젝트 루트에 `compose.yaml`을 작성한다.

```yaml
services:
  app:
    image: eclipse-temurin:17-jre
    command: ["java", "-jar", "/app/app.jar"]
    environment:
      SPRING_PROFILES_ACTIVE: openai,monitoring
      OPENAI_API_KEY: ${OPENAI_API_KEY:?Set OPENAI_API_KEY}
      OPENAI_CHAT_MODEL: ${OPENAI_CHAT_MODEL:?Set OPENAI_CHAT_MODEL}
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./build/libs/observability-lab.jar:/app/app.jar:ro
  prometheus:
    image: prom/prometheus:v3.5.0
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
  grafana:
    image: grafana/grafana:12.4.11
    ports:
      - "127.0.0.1:3000:3000"
    volumes:
      - ./grafana-datasource.yaml:/etc/grafana/provisioning/datasources/prometheus.yaml:ro
      - grafana-data:/var/lib/grafana

volumes:
  prometheus-data:
  grafana-data:
```

`prometheus.yml`에 스크레이프 주소를 지정한다.

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: spring-ai
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["app:8080"]
```

`grafana-datasource.yaml`을 만들면 Grafana가 시작할 때 데이터 소스를 등록한다.

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: spring-ai-prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

[OpenAI 프로파일](04_building_chat_apis_with_openai_and_ollama.md)의 환경 변수를 설정하고 앱을 빌드한다. 이미 8080 포트에서 `bootRun`을 실행 중이면 종료한 뒤 Compose를 실행한다.

```bash
./gradlew bootJar
docker compose config --quiet
docker compose up -d
```

Prometheus의 `http://localhost:9090/targets`에서 `spring-ai`가 `UP`인지 확인한다. Grafana의 `http://localhost:3000`에서 로그인한 뒤 Prometheus 데이터 소스로 패널을 추가한다. 최초 기본 자격 증명으로 로그인한 경우 화면에서 암호를 변경한다. [Grafana Docker 설치](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/) · [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)

## 2. 토큰, 지연, 오류 패널

[채팅 요청 예제](11_measuring_llm_cost_latency_errors_and_quality.md)를 몇 번 실행한다. 최초 시계열이 생긴 뒤 연속된 스크레이프 표본이 쌓이면 조회한다.

**최근 5분 입력·출력 토큰 수**

```promql
sum by (gen_ai_request_model, gen_ai_token_type) (
  increase(gen_ai_client_token_usage_total{
    job="spring-ai", gen_ai_operation_name="chat", gen_ai_token_type=~"input|output"
  }[5m])
)
```

**모델 호출 p95 지연(초)**

```promql
histogram_quantile(0.95,
  sum by (le, gen_ai_request_model) (
    rate(gen_ai_client_operation_seconds_bucket{
      job="spring-ai", gen_ai_operation_name="chat"
    }[5m])
  )
)
```

**채팅 API의 5xx 비율**

```promql
sum(rate(http_server_requests_seconds_count{
  job="spring-ai", uri="/api/chat", status=~"5.."
}[5m]))
/
sum(rate(http_server_requests_seconds_count{
  job="spring-ai", uri="/api/chat"
}[5m]))
```

토큰 패널의 단위는 토큰, 지연은 초, 오류는 0~1 범위의 비율로 설정한다. 요청이 없는 구간이나 아직 5xx 시계열이 없는 구간은 빈 값으로 나타날 수 있다. `increase`는 스크레이프 사이 값을 추정하므로 집계값에 소수점이 생길 수 있다. 개별 요청의 사용량은 [비용 비교 실습](14_analyzing_and_controlling_rag_token_costs.md)의 응답 메타데이터에서 확인한다. [Prometheus Query Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
