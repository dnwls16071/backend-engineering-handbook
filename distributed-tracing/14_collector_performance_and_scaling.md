# Collector Performance and Scaling

Collector를 확장할 때 수신 처리량뿐 아니라 큐 포화, Exporter 오류, CPU와 메모리를 함께 본다. 병목이 백엔드에 있다면 Collector 복제만으로 목적지 처리량을 늘리기 어렵다. [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [Collector 자체 텔레메트리](https://opentelemetry.io/docs/collector/internal-telemetry/) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/)

## 1. 구성 요소별 확장 제약

| 구성 요소 | 확장 시 확인할 점 | 근거 |
| --- | --- | --- |
| Stateless OTLP Gateway | 복제하고 트래픽을 분배한다. gRPC의 장기 연결 때문에 연결별 분배와 인스턴스별 처리량을 확인한다 | [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [Collector 게이트웨이 배포](https://opentelemetry.io/docs/collector/deploy/gateway/) |
| Prometheus Scraper | 복제본마다 같은 대상을 수집할 수 있으므로 스크레이프 대상을 어떻게 배정할지 정한다 | [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) |
| Tail Sampling | Trace ID 기준으로 라우팅하고 대기 창, Trace 수, 메모리 사용량을 기준으로 용량을 검증한다 | [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [Collector Contrib 0.144 Tail Sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.144.0/processor/tailsamplingprocessor/README.md) |

## 2. 병목을 실험으로 구분하기

Collector의 수신 거절, Exporter 큐의 현재 크기와 최대 용량, 전송 실패를 같은 타임라인에 놓는다. 큐가 계속 증가할 때는 목적지 지연·오류를 확인하고 유입 속도와 전송 처리량을 함께 측정한다. [Collector 자체 텔레메트리](https://opentelemetry.io/docs/collector/internal-telemetry/) · [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/)

## 3. 조정 전후를 비교하기

같은 유입 패턴과 조회 성공 기준에서 Batch 크기, Exporter 동시성, Collector 복제 수 중 하나씩 바꾼다. 로컬 실습의 메모리와 배치 수치는 학습을 위한 설정이므로 운영 값은 실제 부하에서 정한다. [Collector 0.144 Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/batchprocessor/README.md) · [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/) · [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [Collector 0.144 Memory Limiter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/memorylimiterprocessor/README.md)
