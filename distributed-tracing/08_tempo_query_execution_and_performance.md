# Tempo Query Execution and Performance

Trace ID를 알고 있을 때는 ID 직접 조회를 쓴다. Span 속성, 상태, 지속 시간, 관계로 후보 Trace를 찾을 때는 TraceQL을 사용한다. [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/)

## 1. 검색이 분할되는 방식

Query Frontend가 검색 작업을 나누고 Querier가 최근 Span 또는 블록을 읽는다. 결과 수 제한과 병렬 작업의 완료 순서 때문에 기본 검색에서 반환한 일부 결과를 전체 장애 건수로 해석할 수 없다. [Tempo 2.10 아키텍처](https://grafana.com/docs/tempo/v2.10.x/introduction/architecture/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [Tempo 검색 성능](https://grafana.com/docs/tempo/v2.10.x/operations/backend_search/)

## 2. 시간과 범위를 먼저 좁히기

장애 시각에 맞춰 조회 시간 범위를 줄이고 서비스·작업·상태 조건을 추가한다. 전체 Trace 지속 시간은 `trace:duration`으로, 개별 Span의 지속 시간은 `span:duration`으로 비교한다. [Tempo 검색 성능](https://grafana.com/docs/tempo/v2.10.x/operations/backend_search/) · [TraceQL 2.10 문법](https://grafana.com/docs/tempo/v2.10.x/traceql/construct-traceql-queries/)

```traceql
{ resource.service.name = "stock" && span:duration > 50ms }
```

## 3. 성능 조정은 검색 결과와 비용을 같이 측정한다

동일한 쿼리와 시간 범위에서 응답 시간, 읽은 데이터 양, 오류를 비교한다. 병렬성을 높일 때는 Querier와 백엔드의 부하도 함께 본다. 반복적으로 쓰는 필터가 병목이라면 전용 컬럼을 검토한다. [Tempo 검색 성능](https://grafana.com/docs/tempo/v2.10.x/operations/backend_search/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/) · [Tempo 전용 속성 컬럼](https://grafana.com/docs/tempo/v2.10.x/operations/dedicated_columns/)
