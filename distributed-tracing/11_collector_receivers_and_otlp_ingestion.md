# Collector Receivers and OTLP Ingestion

Receiver는 외부에서 보낸 텔레메트리를 받거나 지원하는 소스로부터 가져와 신호별 파이프라인에 전달한다. 실습은 애플리케이션이 전송하는 OTLP/HTTP Trace를 받는다. [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md)

## 1. OTLP/HTTP와 OTLP/gRPC를 구분하기

| 전송 방식 | 엔드포인트 규칙 | 실습에서의 역할 | 근거 |
| --- | --- | --- | --- |
| OTLP/HTTP | 기본 포트 4318, Trace 경로 `/v1/traces` | Python SDK → Collector | [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/) · [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md) |
| OTLP/gRPC | 기본 포트 4317, OTLP Trace 서비스를 호출 | Collector → Tempo | [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/) · [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md) · [Tempo v2.10.8 공식 예제](https://raw.githubusercontent.com/grafana/tempo/v2.10.8/example/docker-compose/local/tempo.yaml) |

## 2. 바인딩 주소와 공개 범위

Collector 컨테이너 안에서 OTLP/HTTP Receiver를 `0.0.0.0:4318`에 바인딩하고, Compose 호스트 포트는 `127.0.0.1:14318`로 한정한다. 배포에서 수신 인터페이스, 인증, 암호화는 네트워크 경계에 맞게 설정한다. [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md) · [Docker Compose 포트](https://docs.docker.com/reference/compose-file/services/#ports) · [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/)

## 3. 수신 문제를 조사하는 순서

수신 대기 주소와 호스트 포트 매핑, 클라이언트가 쓰는 프로토콜과 경로, `service.pipelines.traces.receivers` 등록을 확인한다. 수신 후에도 백엔드 조회가 비면 Collector 수신·거절 카운터와 Exporter 로그를 비교한다. [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md) · [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [Collector 자체 텔레메트리](https://opentelemetry.io/docs/collector/internal-telemetry/) · [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/)
