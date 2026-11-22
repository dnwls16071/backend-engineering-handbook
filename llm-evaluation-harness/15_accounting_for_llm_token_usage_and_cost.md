# Accounting for LLM Token Usage and Cost

제공자 응답의 사용량을 시도별로 수집하고, 모델·요율 버전을 적용해 토큰과 추정 비용을 계산한다. 제공자 청구 정보와 비교할 수 있도록 재시도와 Judge 호출을 따로 식별한다. [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md) · [OpenTelemetry GenAI · Metrics](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-metrics.md)

## 1. 실제 호출의 토큰과 미수집을 구분한다

입력·출력 사용량은 제공자가 응답에 알려 준 값을 우선한다. 스트리밍은 사용량이 들어오는 마지막 응답까지 확인하고, 제공자가 주지 않았으면 누락으로 남긴다. 토크나이저로 추정한 경우에는 청구 기준과 구분되는 별도 출처로 표시한다. [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md) · [OpenTelemetry GenAI · Metrics](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-metrics.md)

이 예에서는 OpenTelemetry Semantic Conventions 1.37.0의 개발 상태 GenAI 규약을 고정한다. Span의 gen_ai.usage.input_tokens 및 gen_ai.usage.output_tokens와, 호출 집계의 gen_ai.client.token.usage를 구분한다. 다른 버전의 SDK나 계측 라이브러리는 채택한 규약을 확인한다. [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md) · [OpenTelemetry GenAI · Metrics](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-metrics.md)

## 2. 요청마다 한 번만 합산하고 단가 범위를 명시한다

부모 요청 Span과 하위 모델 호출 Span에서 같은 사용량을 중복 합산하지 않는다. 실제로 비용이 생긴 시도를 구분해 합치고, 캐시 입력 등 단가가 다른 토큰은 제공자의 요금 집계 정의에 맞춰 분리한다. 아래는 캐시 할인이나 기타 요금이 없는 가상의 USD 단가 예제다. [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md) · [OpenTelemetry GenAI · Metrics](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-metrics.md) · [OpenTelemetry · Traces](https://opentelemetry.io/docs/concepts/signals/traces/)

제공자 응답 어댑터는 사용량을 input과 output에 매핑한다. Python 3.12와 opentelemetry-sdk 1.37.0을 사용하는 이 예는 응답 예시를 메모리 exporter로 보내 Span 속성과 비용 계산을 확인한다. [OpenTelemetry · Python Instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/) · [OpenTelemetry Python 1.37.0 · InMemorySpanExporter](https://raw.githubusercontent.com/open-telemetry/opentelemetry-python/v1.37.0/opentelemetry-sdk/src/opentelemetry/sdk/trace/export/in_memory_span_exporter.py) · [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md)

```python
from decimal import Decimal

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

def read_reported_counts(usage):
    counts = {kind: usage.get(kind) for kind in ("input", "output")}
    if any(value is not None and (type(value) is not int or value < 0)
           for value in counts.values()):
        raise ValueError("token counts must be nonnegative integers")
    return counts

def estimate_usd(counts):
    if None in counts.values():
        return None
    return (
        Decimal(counts["input"]) * Decimal("0.50")
        + Decimal(counts["output"]) * Decimal("2.00")
    ) / Decimal("1000000")

exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
tracer = provider.get_tracer("wiki-eval-example")

counts = read_reported_counts({"input": 8000, "output": 1000})
with tracer.start_as_current_span("model.generate") as span:
    for kind, count in counts.items():
        if count is not None:
            span.set_attribute(f"gen_ai.usage.{kind}_tokens", count)

captured, = exporter.get_finished_spans()
assert captured.attributes["gen_ai.usage.input_tokens"] == 8000
assert captured.attributes["gen_ai.usage.output_tokens"] == 1000
assert estimate_usd(counts) == Decimal("0.006")
assert estimate_usd(read_reported_counts({"input": 8000})) is None
provider.shutdown()
```

실제 비용 리포트에서는 제공자, 적용일과 가격 버전, 통화를 남긴다. 사용량 누락은 0으로 더하지 않고 건수와 비율을 공개하며, 계산한 비용은 청구 내역과 대조한다. [OpenTelemetry GenAI · Spans](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-spans.md) · [OpenTelemetry GenAI · Metrics](https://raw.githubusercontent.com/open-telemetry/semantic-conventions/v1.37.0/docs/gen-ai/gen-ai-metrics.md)
