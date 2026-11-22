# Configuring Grafana, OpenTelemetry Collector, and Tempo

로컬 실습은 Tempo, Collector, Grafana의 설정 파일 세 개를 사용한다. 파일을 같은 디렉터리에 저장한 후 [16번 Compose 실습](16_running_the_tracing_stack_with_docker_compose.md)에서 읽기 전용으로 마운트한다. [Tempo v2.10.8 공식 예제](https://raw.githubusercontent.com/grafana/tempo/v2.10.8/example/docker-compose/local/tempo.yaml) · [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [Grafana 데이터 소스 프로비저닝](https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources) · [Docker Bind Mount](https://docs.docker.com/engine/storage/bind-mounts/)

## 1. tempo.yaml에서 수신과 저장을 설정하기

Tempo는 4317에서 Collector의 OTLP/gRPC를 받고 3200에서 조회 요청을 처리한다. 로컬 블록과 WAL의 경로를 지정한다. `max_block_duration: 1m`과 `block_retention: 24h`는 이 실습에서만 사용하는 값이다. [Tempo v2.10.8 공식 예제](https://raw.githubusercontent.com/grafana/tempo/v2.10.8/example/docker-compose/local/tempo.yaml) · [Tempo 2.10 설정](https://grafana.com/docs/tempo/v2.10.x/configuration/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/)

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317

ingester:
  max_block_duration: 1m

compactor:
  compaction:
    block_retention: 24h

storage:
  trace:
    backend: local
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/blocks
```

## 2. collector.yaml에서 Trace 파이프라인을 설정하기

호스트 SDK의 OTLP/HTTP를 받은 뒤 메모리 제한과 배치를 거쳐 Tempo로 전달한다. `tls.insecure: true`는 실습의 Compose 네트워크에서만 쓰는 평문 연결 설정이다. [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md) · [Collector 0.144 OTLP/gRPC Exporter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/exporter/otlpexporter/README.md) · [Collector 0.144 Memory Limiter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/memorylimiterprocessor/README.md) · [Collector 0.144 Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/batchprocessor/README.md)

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 128
    spike_limit_mib: 32
  batch:
    timeout: 1s

exporters:
  otlp_grpc/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp_grpc/tempo]
```

## 3. tempo-datasource.yaml에서 Grafana 조회 주소를 설정하기

Grafana가 내부 서비스 주소 `http://tempo:3200`을 사용하게 한다. 데이터 소스 UID `tempo`는 조회 API나 다른 데이터 소스에서 참조하는 데 쓰인다. [Grafana Tempo 데이터 소스](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/) · [Grafana 데이터 소스 프로비저닝](https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources) · [Docker Compose 네트워킹](https://docs.docker.com/compose/how-tos/networking/)

```yaml
apiVersion: 1
datasources:
  - name: Tempo
    type: tempo
    uid: tempo
    access: proxy
    url: http://tempo:3200
    isDefault: true
    editable: false
```
