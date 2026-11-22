# Instrumenting Three Services with OpenTelemetry

gateway, order, stock을 별도 프로세스로 실행한다. 동일한 코드에서 프로세스마다 역할을 선택하고 OpenTelemetry Resource의 `service.name`으로 구별한다. [OpenTelemetry Python 계측](https://opentelemetry.io/docs/languages/python/instrumentation/) · [Python 3.12 HTTP 서버](https://docs.python.org/3.12/library/http.server.html)

## 1. 어떤 Span이 생기는지 예측하기

gateway와 order는 각각 SERVER Span과 다음 서비스에 대한 CLIENT Span을 만든다. stock은 SERVER Span 한 개를 만든다. 각 HTTP 호출 직전에 현재 CLIENT Span을 헤더에 주입하고, 수신 서버는 헤더에서 부모 컨텍스트를 꺼낸다. [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) · [OpenTelemetry Python 전파](https://opentelemetry.io/docs/languages/python/propagation/) · [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## 2. app.py에서 계측 구현하기

아래 파일은 로컬 실습에서만 사용한다. `?fail=1` 요청이면 stock에서 의도적으로 503을 반환한다. Span 상태를 ERROR로 기록하고 요청 응답과 로그에 Trace ID를 남겨 Grafana에서 같은 요청을 찾는다. [Python 3.12 HTTP 서버](https://docs.python.org/3.12/library/http.server.html) · [OpenTelemetry Python 계측](https://opentelemetry.io/docs/languages/python/instrumentation/) · [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) · [OpenTelemetry 컨텍스트 전파](https://opentelemetry.io/docs/concepts/context-propagation/)

```python
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

ROUTES = {
    "gateway": (18080, "/checkout", "order"),
    "order": (18081, "/orders", "stock"),
    "stock": (18082, "/stock", None),
}

service = sys.argv[1]
port, route, next_service = ROUTES[service]
provider = TracerProvider(resource=Resource.create({"service.name": service}))
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://127.0.0.1:14318/v1/traces", timeout=3),
        schedule_delay_millis=500,
    )
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("distributed-tracing-lab")


def call_service(target, fail):
    target_port, target_route, _ = ROUTES[target]
    url = f"http://127.0.0.1:{target_port}{target_route}?fail={int(fail)}"
    with tracer.start_as_current_span(f"call {target}", kind=SpanKind.CLIENT) as span:
        headers = {}
        propagate.inject(headers)
        try:
            with urlopen(Request(url, headers=headers), timeout=2) as response:
                status = response.status
        except HTTPError as error:
            with error:
                status = error.code
        except (URLError, TimeoutError):
            status = 503
        if status >= 500:
            span.set_status(Status(StatusCode.ERROR))
        return status


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        target = urlsplit(self.path)
        if target.path != route:
            self.send_error(404)
            return

        fail = parse_qs(target.query).get("fail") == ["1"]
        carrier = {key.lower(): value for key, value in self.headers.items()}
        parent = propagate.extract(carrier)
        with tracer.start_as_current_span(
            f"GET {route}", context=parent, kind=SpanKind.SERVER
        ) as span:
            if next_service:
                status = call_service(next_service, fail)
            else:
                sleep(0.08)
                status = 503 if fail else 200
            if status >= 500:
                span.set_status(Status(StatusCode.ERROR))

            context = span.get_span_context()
            trace_id = f"{context.trace_id:032x}"
            body = json.dumps({"service": service, "status": status}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Trace-Id", trace_id)
            self.end_headers()
            self.wfile.write(body)
            print(f"{service} {status} trace_id={trace_id} span_id={context.span_id:016x}", flush=True)


try:
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    provider.shutdown()
```

## 3. 개별 서버 시작하기

[16번 실습](16_running_the_tracing_stack_with_docker_compose.md)을 먼저 시작한다. Python 3.12 가상 환경에 실습과 같은 SDK와 OTLP/HTTP Exporter를 설치한다. 세 실행 명령은 같은 디렉터리의 별도 터미널에서 각각 실행한다. [OpenTelemetry Python 계측](https://opentelemetry.io/docs/languages/python/instrumentation/) · [Python 3.12 HTTP 서버](https://docs.python.org/3.12/library/http.server.html) · [Collector 0.144 OTLP Receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.144.0/receiver/otlpreceiver/README.md)

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install \
  opentelemetry-sdk==1.37.0 opentelemetry-exporter-otlp-proto-http==1.37.0

# 각각 별도 터미널에서 실행
.venv/bin/python app.py stock
.venv/bin/python app.py order
.venv/bin/python app.py gateway
```
