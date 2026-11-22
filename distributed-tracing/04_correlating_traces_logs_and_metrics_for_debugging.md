# Correlating Traces, Logs, and Metrics for Debugging

장애 분석에서는 지표로 영향 범위를 파악하고 Trace에서 멈춘 작업을 찾은 뒤, 같은 Trace ID와 Span ID가 담긴 로그로 실행 조건을 확인한다. [Grafana Trace↔Log 연동](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/configure-trace-to-logs/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/) · [Grafana Explore Traces](https://grafana.com/docs/grafana/latest/visualizations/explore/trace-integration/)

## 1. 503부터 역으로 따라가기

장애 시간대의 gateway 503을 찾고 stock 오류 Span을 검색한다. 워터폴에서 stock이 실제 요청을 받았는지와 order가 어디서 실패했는지 확인한다. stock Span이 비어 있다면 컨텍스트 전파, 계측, 샘플링, 전송 여부를 함께 조사한다. [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/) · [OpenTelemetry 샘플링](https://opentelemetry.io/docs/concepts/sampling/) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/)

## 2. Trace와 로그를 연결하기

애플리케이션 로그에 `trace_id`와 `span_id`를 남긴다. Grafana에서 Tempo → Loki는 Span 속성과 조회 시간 범위를 사용하고, Loki → Tempo는 로그에서 추출한 Trace ID를 링크로 사용한다. Loki를 붙일 때 두 방향을 각각 설정한다. [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/) · [Grafana Trace↔Log 연동](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/configure-trace-to-logs/)

## 3. 전파하는 정보의 범위

`traceparent`에는 Trace ID, 보낸 쪽 Span ID, Trace 플래그가 들어간다. `tracestate`는 추적 시스템별 상태를 전달한다. 외부에서 들어온 헤더의 신뢰 여부는 서비스 경계에서 정하고, 추적 헤더나 Baggage에 비밀과 개인정보를 넣지 않는다. [W3C Trace Context](https://www.w3.org/TR/trace-context/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/)
