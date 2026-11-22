# OpenTelemetry Collector Role and Deployment Patterns

Collector는 서비스에서 보낸 텔레메트리를 받아 처리한 뒤 백엔드로 전송한다. 서비스에서는 SDK가 계측과 컨텍스트 전파를 담당하고, Collector 이후의 저장과 검색은 Tempo 같은 백엔드가 담당한다. [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) · [Tempo 2.10 아키텍처](https://grafana.com/docs/tempo/v2.10.x/introduction/architecture/)

## 1. Agent와 Gateway를 선택하는 기준

| 배치 | 역할과 비용 | 근거 |
| --- | --- | --- |
| Agent | 앱이나 호스트 가까이에서 수집한다. 호스트별 기동과 리소스 관리가 필요하다 | [Collector 에이전트 배포](https://opentelemetry.io/docs/collector/deploy/agent/) |
| Gateway | 여러 앱이 공용 OTLP 엔드포인트를 사용한다. 중앙에서 정책과 내보내기 연결을 관리한다 | [Collector 게이트웨이 배포](https://opentelemetry.io/docs/collector/deploy/gateway/) |
| Agent + Gateway | 로컬에서 수집하고 중앙에서 공통 처리한다. 계층마다 전송 실패와 큐 상태를 관찰한다 | [Collector 에이전트 배포](https://opentelemetry.io/docs/collector/deploy/agent/) · [Collector 게이트웨이 배포](https://opentelemetry.io/docs/collector/deploy/gateway/) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/) |

## 2. 로컬 실습에서의 역할

세 앱은 같은 Collector HTTP Receiver를 사용하고, Collector가 Tempo로 gRPC 전송한다. 앱에서 W3C 헤더를 주입하고 추출해 서비스 경계를 잇는지도 별도로 검증한다. [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/)
