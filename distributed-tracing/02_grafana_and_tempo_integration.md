# Grafana and Tempo Integration

Grafana에서 Tempo 데이터 소스는 Trace ID나 TraceQL 요청을 Tempo로 보내고, 반환된 Span을 트리와 타임라인으로 펼친다. [Grafana Tempo 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/)

## 1. 수집 주소와 조회 주소

| 호출자 | 실습 주소 | 용도 | 근거 |
| --- | --- | --- | --- |
| 애플리케이션 SDK | `http://127.0.0.1:14318/v1/traces` | Collector에 OTLP/HTTP Trace 전송 | [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/) · [Docker Compose 포트](https://docs.docker.com/reference/compose-file/services/#ports) |
| Collector | `tempo:4317` | Tempo Distributor에 OTLP/gRPC 전송 | [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/) · [Tempo v2.10.8 공식 예제](https://raw.githubusercontent.com/grafana/tempo/v2.10.8/example/docker-compose/local/tempo.yaml) |
| Grafana 서버 | `http://tempo:3200` | Compose 내부에서 Tempo HTTP 조회 | [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [Grafana Tempo 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/) · [Docker Compose 네트워킹](https://docs.docker.com/compose/how-tos/networking/) |
| 브라우저 | `http://127.0.0.1:13000` | Grafana Explore 접속 | [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/) · [Docker Compose 포트](https://docs.docker.com/reference/compose-file/services/#ports) |

## 2. 하나의 Trace를 찾는 두 방법

이미 응답 헤더나 로그에서 Trace ID를 얻었다면 ID로 직접 조회한다. ID가 없다면 시간 범위를 정하고 `resource.service.name`, Span 상태 같은 조건으로 후보를 찾은 뒤 하나를 연다. [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/)

## 3. 데이터 소스 연결 문제부터 분리하기

Tempo의 `/ready`와 `/api/echo`로 조회 경로를 확인한다. 호스트에서 Tempo API가 열리고 Grafana에서만 조회가 실패하면 Grafana 서버 기준 데이터 소스 URL과 컨테이너 네트워크를 확인한다. [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [Grafana Tempo 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/) · [Docker Compose 네트워킹](https://docs.docker.com/compose/how-tos/networking/)
