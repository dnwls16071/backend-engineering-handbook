# Collector Processors for Batching, Memory, and Sampling

Processor는 설정 순서대로 신호를 처리한다. 메모리 제한, 샘플링, 배치의 위치가 달라지면 같은 입력에서 버퍼링과 전송 시점도 달라질 수 있다. [Collector 구성](https://opentelemetry.io/docs/collector/configuration/) · [Collector 0.144 Memory Limiter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/memorylimiterprocessor/README.md) · [Collector 0.144 Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/batchprocessor/README.md) · [Collector Contrib 0.144 Tail Sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.144.0/processor/tailsamplingprocessor/README.md)

## 1. Memory Limiter를 먼저 배치하기

Memory Limiter는 메모리를 주기적으로 검사하고 소프트 한도를 넘으면 데이터를 일시적으로 거절한다. 실습의 `limit_mib: 128`과 `spike_limit_mib: 32`로 계산한 소프트 한도는 96 MiB다. 거절 후 재시도 가능 여부는 앞단 Receiver와 송신자의 동작에 달려 있다. [Collector 0.144 Memory Limiter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/memorylimiterprocessor/README.md) · [OTLP 명세](https://opentelemetry.io/docs/specs/otlp/)

## 2. Batch로 전송 횟수 줄이기

Batch는 크기와 시간 조건을 기준으로 보낼 데이터를 묶는다. `send_batch_size`는 배치를 내보내는 트리거이고, 상한은 `send_batch_max_size`로 설정한다. 실습은 Batch 처리로 인해 요청 응답과 Trace 조회 사이에 시간이 생길 수 있다. [Collector 0.144 Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/processor/batchprocessor/README.md)

## 3. Tail Sampling은 Trace 단위 정책이다

Tail Sampling은 지연 시간이나 오류 상태 등 모인 Span을 근거로 Trace를 선택한다. Collector Contrib의 Tail Sampling Processor가 동작하려면 같은 Trace의 Span을 한 인스턴스로 보내야 한다. 대기 창보다 늦게 도착한 Span도 고려해 정책과 메모리 크기를 정한다. [Collector Contrib 0.144 Tail Sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.144.0/processor/tailsamplingprocessor/README.md) · [Collector 확장](https://opentelemetry.io/docs/collector/scaling/) · [OpenTelemetry 샘플링](https://opentelemetry.io/docs/concepts/sampling/)
