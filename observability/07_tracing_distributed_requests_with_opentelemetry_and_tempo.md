# Tracing Distributed Requests with OpenTelemetry and Tempo

## 1. 게시글 조회 한 건을 Trace로 따라간다

`GET /api/posts`를 처리하는 `sns-api`가 Go 서비스 `sns-recommend`에서 추천 목록을 조회한다고 가정한다. Trace는 이 요청에서 발생한 작업을 같은 Trace ID로 묶는다. Span은 서버 요청 처리, 외부 HTTP 호출, 추천 조회처럼 시작과 끝이 있는 작업 하나를 기록한다. Span마다 고유한 Span ID가 있고, 자식 Span은 부모의 Span ID를 참조한다. [kind의 SNS API 배포](02_deploying_spring_boot_on_kind_with_gateway_api.md), [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)

```text
sns-api        SERVER    GET /api/posts
└─ sns-api     CLIENT    GET /recommendations
   └─ sns-recommend SERVER   GET /recommendations
      └─ sns-recommend INTERNAL recommendation.lookup
```

Spring의 HTTP 클라이언트는 요청에 W3C `traceparent` 헤더를 넣는다. 헤더에는 같은 Trace ID, 호출하는 CLIENT Span의 ID, 샘플링 플래그가 들어간다. Go의 HTTP 계측은 이 헤더를 읽어 CLIENT Span을 부모로 두는 SERVER Span을 만든다. 추천 조회 Span은 Go 요청의 `context.Context`를 받아 SERVER Span의 자식이 된다. [W3C Trace Context](https://www.w3.org/TR/trace-context/#traceparent-header), [OpenTelemetry Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)

| 보내는 쪽 | 받는 쪽 | 전달하는 데이터 |
| :--- | :--- | :--- |
| `sns-api` | `sns-recommend.sns.svc.cluster.local:8080` | 추천 조회 HTTP 요청과 `traceparent` |
| 두 앱의 OTLP Exporter | `otel-collector.observability.svc.cluster.local:4318` | OTLP/HTTP로 내보낸 Span |
| OpenTelemetry Collector | `tempo.observability.svc.cluster.local:4317` | OTLP/gRPC로 전송한 Span |
| Grafana | `tempo.observability.svc.cluster.local:3200` | TraceQL 검색과 Trace ID 조회 |

## 2. Spring Boot에서 서버와 HTTP 클라이언트를 계측한다

아래는 Spring Boot 3.5의 설정이다. 기존 Actuator 의존성에 Micrometer Tracing의 OpenTelemetry 브리지와 OTLP Exporter를 추가한다. 서버 요청과 Spring의 HTTP 클라이언트 계측을 통해 Span을 만들고 Collector의 OTLP/HTTP 수신기로 보낸다. [Spring Boot 3.5 Tracing](https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html)

```groovy
dependencies {
    implementation 'io.micrometer:micrometer-tracing-bridge-otel'
    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
}
```

기존 `application.yml`에 아래 항목을 병합한다. `service.name`은 Tempo에서 검색할 서비스 이름이다. 실습에서는 새 Trace의 샘플링 확률을 `1.0`으로 두어 요청을 쉽게 확인한다. [Spring Boot 3.5 속성](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html), [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/)

```yaml
spring:
  application:
    name: sns-api
management:
  opentelemetry:
    resource-attributes:
      "[service.name]": sns-api
  tracing:
    propagation:
      type: W3C
    sampling:
      probability: 1.0
  otlp:
    tracing:
      transport: http
      endpoint: http://otel-collector.observability.svc.cluster.local:4318/v1/traces
```

`RecommendationClient`를 컴포넌트 스캔 범위에 두고, 기존 `GET /api/posts` 처리 코드의 추천 조회 지점에서 주입받아 `fetch()`를 호출한다. Spring Boot가 자동 구성한 `RestClient.Builder`를 사용하면 `RestClient` 호출에 CLIENT Span과 W3C 헤더가 연결된다. [Spring Boot 3.5의 Trace 전파](https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html#actuator.tracing.propagating-traces)

```java
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class RecommendationClient {
    private final RestClient client;

    RecommendationClient(RestClient.Builder builder) {
        this.client = builder.baseUrl("http://sns-recommend:8080").build();
    }

    public String[] fetch() {
        return this.client.get()
                .uri("/recommendations")
                .retrieve()
                .body(String[].class);
    }
}
```

`sns-api`와 `sns-recommend`를 같은 `sns` Namespace에 배포하므로 짧은 Service 이름 `sns-recommend`로 접속할 수 있다. Jib으로 새 태그를 빌드하고 kind에 로드한 뒤 `sns-api` Deployment의 이미지 태그를 갱신한다. [Kubernetes Service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [SNS 이미지 롤아웃](02_deploying_spring_boot_on_kind_with_gateway_api.md#3-spring-boot-deployment와-service-연결하기)

## 3. Go에서 부모 Span을 이어받고 추천 조회를 기록한다

Go 서비스 시작 시 OTLP/HTTP Exporter와 TracerProvider를 구성한다. `otelhttp.NewHandler`는 W3C 헤더를 읽어 SERVER Span을 시작하고 새 요청 컨텍스트를 핸들러에 전달한다. 아래 코드는 고정 추천 목록을 반환하는 실습용으로, `recommendation.lookup`에 캐시 미스 경로를 가정한 속성을 기록한다. 실제 캐시와 연결할 때는 조회 결과에 따라 이 속성값을 정한다. [OpenTelemetry Go 계측](https://opentelemetry.io/docs/languages/go/instrumentation/), [`otelhttp` API](https://pkg.go.dev/go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp)

```go
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func recommendations(ctx context.Context) []string {
	_, span := otel.Tracer("sns-recommend").Start(ctx, "recommendation.lookup")
	defer span.End()
	span.SetAttributes(attribute.String("recommendation.path", "cache_miss"))
	return []string{"post-42", "post-84"}
}

func run() (err error) {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	exporter, err := otlptracehttp.New(ctx)
	if err != nil {
		return err
	}
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithResource(resource.NewSchemaless(attribute.String("service.name", "sns-recommend"))),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.AlwaysSample())),
		sdktrace.WithBatcher(exporter),
	)
	defer func() {
		flushCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		err = errors.Join(err, provider.Shutdown(flushCtx))
	}()
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	mux := http.NewServeMux()
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(recommendations(r.Context())); err != nil {
			log.Print(err)
		}
	})
	mux.Handle("GET /recommendations", otelhttp.NewHandler(handler, "GET /recommendations"))
	server := &http.Server{Addr: ":8080", Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	serveErr := make(chan error, 1)
	go func() { serveErr <- server.ListenAndServe() }()

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return server.Shutdown(shutdownCtx)
	}
}

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}
```

`ParentBased`는 상위 서비스의 샘플링 결정을 따르고, 종료 시 Provider가 대기 중인 Span을 내보낸다. `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`는 HTTP 스킴과 `/v1/traces`까지 포함하는 주소다. [Go OTLP/HTTP Exporter 설정](https://pkg.go.dev/go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp), [OpenTelemetry Go TracerProvider](https://pkg.go.dev/go.opentelemetry.io/otel/sdk/trace#TracerProvider)

새 디렉터리에 `main.go`와 아래 `Dockerfile`을 저장한다. Go 1.25 이상에서 모듈과 Linux 바이너리를 만든 뒤 이미지를 kind에 로드한다. 빌드 호스트와 kind 노드의 CPU 아키텍처가 다르면 Go 빌드의 `GOARCH`와 Docker 빌드의 `--platform`을 노드에 맞춘다. [Go `otelhttp` v0.64.0](https://pkg.go.dev/go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp@v0.64.0), [kind 이미지 로드](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster)

```dockerfile
FROM scratch
COPY sns-recommend /sns-recommend
ENTRYPOINT ["/sns-recommend"]
```

```bash
go mod init example.com/sns-recommend
go get go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp@v0.64.0 \
  go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp@v1.39.0
go mod tidy
CGO_ENABLED=0 GOOS=linux go build -o sns-recommend .
docker build -t sns-recommend:tracing .
kind load docker-image sns-recommend:tracing --name sns

kubectl --context kind-sns -n sns create deployment sns-recommend \
  --image=sns-recommend:tracing --port=8080
kubectl --context kind-sns -n sns set env deployment/sns-recommend \
  OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4318/v1/traces
kubectl --context kind-sns -n sns expose deployment sns-recommend --port=8080 --target-port=8080
kubectl --context kind-sns -n sns rollout status deployment/sns-recommend --timeout=120s
```

## 4. Collector의 traces 파이프라인을 Tempo에 연결한다

`observability` Namespace에 Trace 수집용 Collector를 Deployment로 띄운다. 앞 편의 `otel-logs` DaemonSet은 노드의 로그 파일을 읽고, 여기서 설치하는 `otel-collector`의 ClusterIP Service는 앱이 전송하는 Span을 `4318`번 포트에서 받는다. 아래를 `otel-traces-values.yaml`로 저장한다. OTLP 수신기에서 받은 Span은 `batch`를 거쳐 Tempo의 OTLP/gRPC 수신기로 전송된다. [Spring Boot 로그 수집](06_centralizing_spring_boot_logs_with_opentelemetry_and_loki.md), [Collector Helm 설정](https://github.com/open-telemetry/opentelemetry-helm-charts/blob/opentelemetry-collector-0.179.0/charts/opentelemetry-collector/values.yaml), [Collector 구성](https://opentelemetry.io/docs/collector/configuration/)

```yaml
mode: deployment
fullnameOverride: otel-collector
image:
  repository: otel/opentelemetry-collector-contrib
command:
  name: otelcol-contrib
resources:
  limits:
    memory: 256Mi
service:
  type: ClusterIP
ports:
  otlp: {enabled: false}
  otlp-http: {enabled: true}
  jaeger-compact: {enabled: false}
  jaeger-thrift: {enabled: false}
  jaeger-grpc: {enabled: false}
  zipkin: {enabled: false}
config:
  receivers:
    otlp:
      protocols:
        grpc: null
        http:
          endpoint: 0.0.0.0:4318
    jaeger: null
    prometheus: null
    zipkin: null
  exporters:
    debug: null
    otlp_grpc/tempo:
      endpoint: tempo.observability.svc.cluster.local:4317
      tls:
        insecure: true
  service:
    pipelines:
      logs: null
      metrics: null
      traces:
        receivers: [otlp]
        processors: [memory_limiter, batch]
        exporters: [otlp_grpc/tempo]
```

Tempo는 Span을 받아 저장하고 Grafana의 조회 요청에 응답한다. 이 실습에서는 같은 Namespace에 단일 바이너리 Tempo를 배포한다. 아래 설정을 `tempo.yaml`에 저장한다. 로컬 저장 경로는 실습용 `emptyDir`에 두므로 Pod를 교체하면 기존 Trace가 사라진다. 평문 전송은 로컬 kind 실습을 전제로 한다. [Tempo 배포 방식](https://grafana.com/docs/tempo/latest/reference-tempo-architecture/deployment-modes/), [Tempo 로컬 구성 예시](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/deploy/locally/linux/), [Collector에서 Tempo로 전송](https://grafana.com/docs/tempo/latest/set-up-for-tracing/instrument-send/set-up-collector/otel-collector/)

```yaml
server:
  http_listen_port: 3200
distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
storage:
  trace:
    backend: local
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/blocks
```

다음은 `tempo-k8s.yaml`이다. Tempo의 Service는 Collector가 쓸 `4317`번 포트와 Grafana가 쓸 `3200`번 포트를 노출한다. [Tempo 3.0.2 이미지 설정](https://github.com/grafana/tempo/blob/v3.0.2/cmd/tempo/Dockerfile), [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tempo
spec:
  replicas: 1
  selector:
    matchLabels: {app: tempo}
  template:
    metadata:
      labels: {app: tempo}
    spec:
      securityContext:
        fsGroup: 10001
      containers:
        - name: tempo
          image: grafana/tempo:3.0.2
          args: ["-config.file=/etc/tempo/tempo.yaml", "-target=all"]
          ports:
            - {name: http, containerPort: 3200}
            - {name: otlp-grpc, containerPort: 4317}
          readinessProbe:
            httpGet: {path: /ready, port: http}
          volumeMounts:
            - {name: config, mountPath: /etc/tempo, readOnly: true}
            - {name: data, mountPath: /var/tempo}
      volumes:
        - name: config
          configMap: {name: tempo-config}
        - name: data
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: tempo
spec:
  selector: {app: tempo}
  ports:
    - {name: http, port: 3200, targetPort: http}
    - {name: otlp-grpc, port: 4317, targetPort: otlp-grpc}
```

앞 편에서 생성한 `observability` Namespace에 Tempo와 Collector를 배포한다. [Collector Helm Chart 설치](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/)

```bash
kubectl --context kind-sns -n observability create configmap tempo-config \
  --from-file=tempo.yaml --dry-run=client -o yaml |
  kubectl --context kind-sns -n observability apply -f -
kubectl --context kind-sns -n observability apply -f tempo-k8s.yaml
kubectl --context kind-sns -n observability rollout status deploy/tempo --timeout=120s

helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  --version 0.179.0 --kube-context kind-sns -n observability \
  -f otel-traces-values.yaml --wait
kubectl --context kind-sns -n observability get svc otel-collector tempo
```

## 5. Grafana에서 두 서비스가 이어진 Trace를 확인한다

Grafana에 **Tempo** 데이터 소스를 추가하고 URL에 `http://tempo.observability.svc.cluster.local:3200`을 입력한 뒤 **Save & test**를 실행한다. [메트릭 실습](05_monitoring_spring_boot_with_prometheus_and_grafana.md)의 `monitoring` Namespace에 있는 Grafana에서도 이 주소를 사용한다. [Grafana Tempo 데이터 소스 설정](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)

앞 편처럼 Traefik의 `8081`번 포트 포워딩을 열어 두고 아래 요청을 실행한다. 앱의 내보내기와 Collector의 배치 처리에 몇 초가 걸릴 수 있다.

```bash
curl -fsS -H 'Host: sns.localhost' http://127.0.0.1:8081/api/posts
```

Grafana **Explore**에서 Tempo 데이터 소스와 최근 시간 범위를 고른다. **TraceQL**에서 첫 번째 검색식을 실행해 `sns-api`가 있는 Trace를 찾고, 두 번째 검색식으로 `sns-recommend` Span이 `sns-api` Span의 하위에 있는 Trace로 좁힌다. 각 검색식은 따로 실행한다. [TraceQL 구조 연산자](https://grafana.com/docs/tempo/latest/traceql/construct-traceql-queries/), [Grafana TraceQL 편집기](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-editor/)

```traceql
{ resource.service.name = "sns-api" }
```

```traceql
{ resource.service.name = "sns-api" } >> { resource.service.name = "sns-recommend" }
```

검색 결과의 Trace를 열어 `sns-api` SERVER → CLIENT → `sns-recommend` SERVER → `recommendation.lookup` 순서로 부모·자식 관계를 확인한다. 타임라인에서 추천 호출과 내부 조회의 시작 시각과 지속 시간을 비교한다. 이 동기 호출 흐름에서는 부모 Span의 구간에 자식 Span의 구간이 들어가므로 `GET /api/posts`의 처리 시간은 `sns-api` SERVER Span에서 읽는다. 요청 처리 중 남긴 로그에 MDC `traceId`가 있으면 Explore의 TraceQL 편집기에 ID를 그대로 입력해 해당 Trace를 연다. [Grafana Trace 뷰](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/), [Trace ID로 조회하기](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-editor/#query-by-traceid), [Spring Boot 로그 상관관계](https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html#actuator.tracing.logging-correlation-ids)

| 조회 결과 | 확인할 곳 |
| :--- | :--- |
| 새 Trace가 보이지 않는다 | 조회 시간 범위, 앱 샘플링 설정, Collector의 `traces` 파이프라인 및 Tempo exporter 오류를 확인한다. |
| `sns-api`만 보인다 | `GET /api/posts`에서 추천 호출이 실행됐는지, `sns-recommend` Service와 Go Exporter가 연결됐는지 확인한다. |
| 두 서비스를 각각 찾을 수 있고 Trace ID가 다르다 | Spring의 `RestClient.Builder` 주입, HTTP `traceparent` 전파, Go의 W3C propagator와 `otelhttp` 핸들러를 확인한다. |
