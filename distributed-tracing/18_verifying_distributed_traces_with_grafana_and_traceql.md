# Verifying Distributed Traces with Grafana and TraceQL

[17번 앱](17_instrumenting_three_services_with_opentelemetry.md)이 실행 중일 때 정상 요청과 의도적 실패 요청을 생성한다. 응답의 `X-Trace-Id`로 워터폴을 확인하고 TraceQL 조건으로 실패 건을 찾는다. [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/)

## 1. 정상과 실패 요청 만들기

첫 요청은 200, 두 번째는 503을 기대한다. 각 응답 헤더에서 Trace ID를 복사한다. Exporter와 Collector의 배치가 전송될 시간을 준 뒤 조회한다. [OpenTelemetry Python 계측](https://opentelemetry.io/docs/languages/python/instrumentation/) · [Collector 0.144 Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/batchprocessor/README.md) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/)

```bash
curl -i http://127.0.0.1:18080/checkout
curl -i 'http://127.0.0.1:18080/checkout?fail=1'
```

## 2. Grafana Explore에서 워터폴과 오류 검색 확인하기

`http://127.0.0.1:13000`에서 Grafana에 로그인하고 Explore에서 Tempo를 선택한다. 새 실습 볼륨에서 처음 로그인할 때 기본 사용자 이름과 비밀번호는 각각 `admin`이다. Trace ID로 각각 조회해 gateway → order → stock이 하나의 트리인지 확인한다. 정상과 실패 요청 모두 Span 5개를 기대한다. [Grafana 초기 로그인](https://grafana.com/docs/grafana/latest/setup-grafana/sign-in-to-grafana/) · [Grafana Tempo 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/) · [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)

동일한 시간 범위에서 아래 TraceQL을 실행한다. 첫 줄은 stock 서비스 Span을 찾고, 두 번째 줄은 stock의 오류 Span으로 좁힌다. 세 번째 줄은 50ms를 넘는 stock Span을 찾아 지연 기준을 별도로 확인한다. [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/)

```traceql
{ resource.service.name = "stock" }
{ resource.service.name = "stock" && span:status = error }
{ resource.service.name = "stock" && span:duration > 50ms }
```

## 3. Tempo API로 교차 확인하기

Grafana에서 결과가 비면 같은 Trace ID의 조회와 TraceQL 검색을 Tempo API에 직접 보낸다. Trace ID 조회는 Span 트리 확인에 쓰고, 오류 검색은 두 요청 중 실패 Trace ID만 반환되는지 본다. 지난 실습의 요청이 섞이면 응답 헤더의 ID를 기준으로 대조한다. [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/)

```bash
TRACE_ID='<응답 헤더의 Trace ID>'
curl -fsS -H 'Accept: application/json' \
  "http://127.0.0.1:13200/api/traces/${TRACE_ID}"

curl -fsSG 'http://127.0.0.1:13200/api/search' \
  --data-urlencode 'q={ resource.service.name = "stock" && span:status = error }'
```

## 4. Trace가 비거나 끊겨 보이는 경우

검색 시간 범위와 Trace ID를 먼저 확인한다. 모든 Trace가 비면 SDK → Collector → Tempo 전송과 데이터 소스 URL을 확인한다. 일부 서비스만 빠지면 Resource의 이름, Span 종료, 헤더 주입·추출, 샘플링과 Exporter 오류를 점검한다. [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/) · [OpenTelemetry Python 계측](https://opentelemetry.io/docs/languages/python/instrumentation/) · [OpenTelemetry 샘플링](https://opentelemetry.io/docs/concepts/sampling/) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/)
