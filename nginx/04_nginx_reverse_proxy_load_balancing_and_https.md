# NGINX Reverse Proxy, Load Balancing, and HTTPS

NGINX로 HTTP API와 WebSocket을 백엔드에 전달하고, API 요청을 두 인스턴스에 분산한다. 마지막에는 클라이언트가 HTTPS와 HTTP/2로 접속해도 NGINX가 백엔드와는 HTTP/1.1로 통신하는 구성을 확인한다.

## 1. HTTP/1.0과 HTTP/1.1 리버스 프록시

NGINX는 클라이언트 연결을 받은 뒤, `proxy_pass`로 지정한 업스트림에 별도 요청을 보낸다. `proxy_http_version`은 이 두 구간 중 **NGINX에서 업스트림으로 보내는 요청**의 버전을 설정한다. 기본값은 NGINX 1.29.7부터 HTTP/1.1이며, 이전 버전에서는 HTTP/1.0이다. 예제에서는 버전 차이에 관계없이 같은 설정이 적용되도록 HTTP/1.1을 명시한다.

| `location /api/` 안의 설정 | `/api/who?lang=ko`를 요청할 때 업스트림이 받는 경로 |
| --- | --- |
| `proxy_pass http://app_pool;` | `/api/who?lang=ko` |
| `proxy_pass http://app_pool/;` | `/who?lang=ko` |

이 예제처럼 일반 접두어 `location`을 쓸 때 `proxy_pass`에 URI를 지정하면 매칭된 접두어가 지정한 URI로 바뀐다. 백엔드 라우트가 `/api/`를 포함하는지에 맞춰 선택한다.

백엔드 주소가 DNS를 통해 바뀌는 환경에서는 NGINX 1.27.3 이상 오픈소스 버전에서 `upstream`의 `zone`, `resolver`, `server ... resolve`를 조합해 주소 변경을 자동으로 반영할 수 있다. 아래 실습은 고정된 루프백 주소를 사용한다.

**공식 문서** [proxy_pass와 URI 매핑](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass) · [proxy_http_version](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_http_version) · [업스트림 DNS resolve](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#server)

## 2. WebSocket 프록시와 연결 테스트

이 실습에서는 HTTP/1.1 핸드셰이크로 WebSocket 연결을 업그레이드한다. `Upgrade`와 `Connection`은 한 구간에만 적용되는 헤더여서 NGINX가 업스트림 요청에 명시적으로 설정해야 한다. `http`의 `map`으로 클라이언트가 업그레이드를 요청했을 때만 `Connection: upgrade`를 보낸다.

업스트림이 `101 Switching Protocols`로 응답하면 NGINX는 클라이언트와 백엔드 사이에서 데이터를 전달한다. 테스트에서는 연결 성공에 이어 메시지를 보내고 같은 내용을 돌려받는지 확인한다. `proxy_read_timeout`은 업스트림에서 연속된 두 읽기 사이의 대기 한도다. 장시간 유휴 연결이 필요하면 서버의 Ping 간격과 이 한도를 함께 설정한다.

**공식 문서** [NGINX WebSocket 프록시](https://nginx.org/en/docs/http/websocket.html) · [proxy_read_timeout](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_read_timeout)

## 3. 업스트림 로드 밸런싱 방식 5가지

| 방식 | 설정 | 선택 기준 |
| --- | --- | --- |
| Round Robin | 별도 지시어 없이 `server` 목록 선언 | 가중치를 반영해 순환 분배한다. 요청 비용과 서버 용량이 비슷할 때 출발점으로 쓴다. |
| Least Connections | `least_conn;` | 활성 연결이 적은 서버를 가중치와 함께 고려한다. 처리 시간이 고르지 않은 요청에 적합하다. |
| IP Hash | `ip_hash;` | 클라이언트 IP를 기준으로 서버를 선택한다. 여러 클라이언트가 같은 NAT를 사용하면 분배가 치우칠 수 있다. |
| Generic Hash | `hash $uri consistent;` | 직접 고른 키로 서버를 선택한다. `consistent`를 사용하면 서버를 추가하거나 제거할 때 이동하는 키를 줄일 수 있다. |
| Random | `random;` | 가중치를 반영해 임의의 서버를 고른다. `random two least_conn;`은 두 후보를 뽑은 뒤 활성 연결이 적은 쪽을 선택한다. |

실습은 기본 Round Robin을 사용한다. 두 백엔드가 각각 자신의 이름을 반환하게 해 어느 서버가 응답했는지 확인한다. 로드 밸런싱 방식을 바꿀 때는 `upstream` 안에서 한 가지를 선택한다.

**공식 문서** [NGINX HTTP 로드 밸런싱](https://nginx.org/en/docs/http/load_balancing.html) · [업스트림 모듈](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)

## 4. 프록시 성능 설정과 측정

| 설정 | 조정 기준 |
| --- | --- |
| `keepalive 16;` | 워커마다 재사용할 유휴 업스트림 연결을 최대 16개 보관한다. 전체 연결 수 상한과 구분한다. 업스트림이 HTTP/1.1 연결 재사용을 지원해야 하며, 예제는 `Connection` 헤더를 비워 재사용이 가능하게 한다. |
| `proxy_buffering` | 기본값은 `on`이다. 업스트림 응답을 먼저 읽어 클라이언트 전송과 분리한다. SSE처럼 이벤트를 바로 전송해야 하는 경로에서는 `off`를 검토한다. |
| `proxy_connect_timeout`, `proxy_read_timeout` | 연결을 맺는 데 걸리는 시간과 응답을 다음번 읽기까지 기다리는 시간을 각각 설정한다. 일반 API와 장시간 연결은 기대 동작에 맞춰 값을 나눈다. |
| `proxy_cache` | 여러 요청에 동일하게 반환할 수 있는 응답의 백엔드 호출을 줄인다. 캐시 키와 만료 정책을 먼저 정한다. |

같은 요청 패턴에서 처리량, p95 응답 시간, 오류율, 업스트림 연결 수를 비교한다. 로그의 `$request_time`과 `$upstream_response_time`을 함께 보면 지연이 백엔드 응답에서 발생했는지 범위를 좁히는 데 도움이 된다.

**공식 문서** [업스트림 keepalive](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#keepalive) · [프록시 응답 버퍼링](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering) · [proxy_cache](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache) · [NGINX 로그 변수](https://nginx.org/en/docs/http/ngx_http_log_module.html#variables)

## 5. CA 인증서 적용과 HTTP/2

HTTPS를 제공할 때 `listen ... ssl;`과 함께 `ssl_certificate`에 서버 인증서 체인을, `ssl_certificate_key`에 대응하는 개인 키를 지정한다. 중간 인증서가 있다면 PEM 파일에 서버 인증서를 먼저 두고 중간 인증서를 이어 붙인다. 클라이언트는 신뢰하는 CA로 이어지는 인증서 체인과 접속 호스트 이름을 검증한다.

`ngx_http_v2_module`을 포함한 NGINX 1.25.1 이상에서는 `http2 on;`으로 HTTP/2를 활성화한다. HTTPS에서 클라이언트와 NGINX는 TLS 핸드셰이크 중 ALPN으로 `h2`를 협상한다. `curl --http2`로 요청한 뒤 `%{http_version}` 값이 `2`인지 확인한다. 앞단에서 HTTP/2를 쓰더라도 뒷단 버전은 `proxy_http_version`이 결정한다.

**공식 문서** [NGINX HTTPS와 인증서 체인](https://nginx.org/en/docs/http/configuring_https_servers.html#chains) · [NGINX HTTP/2 모듈](https://nginx.org/en/docs/http/ngx_http_v2_module.html#http2)

## 6. 실습 · HTTP API 두 개와 WebSocket을 프록시하기

NGINX 1.25.1 이상과 SSL·HTTP/2 모듈, Python 3.9 이상, OpenSSL, HTTP/2를 지원하는 curl이 필요하다. 실습에 쓰는 포트는 모두 루프백에 바인딩한다. 포트가 이미 사용 중이면 백엔드 코드, NGINX 설정, 테스트 명령에서 함께 바꾼다.

### 백엔드 준비

다음 블록은 임시 가상환경에 WebSocket 라이브러리를 설치한다. 두 HTTP 백엔드는 받은 HTTP 버전과 경로를 반환하고, WebSocket 백엔드는 받은 메시지를 그대로 돌려준다.

```sh
lab_dir="$(mktemp -d)"
cd "$lab_dir" || exit 1
python3 -m venv .venv
.venv/bin/python -m pip install 'websockets==15.0.1'

cat > backend.py <<'PY'
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from websockets.asyncio.server import serve


class App(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        body = f"{self.server.server_port} {self.request_version} {self.path}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def echo(connection):
    async for message in connection:
        await connection.send(message)


async def main():
    for port in (18091, 18092):
        server = ThreadingHTTPServer(("127.0.0.1", port), App)
        Thread(target=server.serve_forever, daemon=True).start()

    async with serve(echo, "127.0.0.1", 18093) as websocket_server:
        print("backends ready", flush=True)
        await websocket_server.serve_forever()


asyncio.run(main())
PY

.venv/bin/python backend.py > backend.log 2>&1 &
backend_pid=$!
```

`backend.log`에 `backends ready`가 표시되면 세 백엔드가 모두 연결을 받을 준비를 마친 것이다. 표시되지 않으면 로그에서 포트 충돌이나 초기화 오류를 확인한다.

### 실습용 CA 및 NGINX 설정

임시 CA가 `proxy.test` 인증서를 서명한다. 테스트할 때만 `curl --cacert`로 이 CA를 지정하면 시스템의 신뢰 저장소를 변경하지 않고도 인증서를 검증할 수 있다. 아래 코드는 같은 터미널에서 실행한다.

```sh
cat > tls.cnf <<'CONF'
[req]
distinguished_name = dn

[dn]

[ca_ext]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign

[server_ext]
basicConstraints = critical,CA:FALSE
keyUsage = digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:proxy.test
CONF

(
    umask 077
    openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
        -subj '/CN=NGINX Lab CA' -config tls.cnf -extensions ca_ext \
        -keyout ca.key -out ca.crt &&
    openssl req -new -newkey rsa:2048 -nodes -subj '/CN=proxy.test' \
        -config tls.cnf -keyout server.key -out server.csr &&
    openssl x509 -req -in server.csr -days 7 \
        -CA ca.crt -CAkey ca.key -CAcreateserial \
        -extfile tls.cnf -extensions server_ext -out server.crt
)
```

```sh
cat > nginx.conf <<'CONF'
worker_processes 1;
pid nginx.pid;
error_log error.log warn;

events {
    worker_connections 256;
}

http {
    map $http_upgrade $connection_upgrade {
        default upgrade;
        ''      close;
    }

    upstream app_pool {
        server 127.0.0.1:18091;
        server 127.0.0.1:18092;
        keepalive 16;
    }

    server {
        listen 127.0.0.1:18083;
        listen 127.0.0.1:18443 ssl;
        server_name proxy.test;

        ssl_certificate     server.crt;
        ssl_certificate_key server.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        http2 on;

        location /api/ {
            proxy_pass http://app_pool/;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location = /ws {
            proxy_pass http://127.0.0.1:18093;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_read_timeout 75s;
        }
    }
}
CONF

nginx -p "$lab_dir/" -c nginx.conf -t &&
    nginx -p "$lab_dir/" -c nginx.conf
```

### HTTP, WebSocket, HTTPS 확인

```sh
curl -fsS --http1.0 'http://127.0.0.1:18083/api/who?lang=ko'
curl -fsS --http1.1 'http://127.0.0.1:18083/api/who?lang=ko'

.venv/bin/python - <<'PY'
from websockets.sync.client import connect

with connect("ws://127.0.0.1:18083/ws", proxy=None) as client:
    client.send("ping")
    print(client.recv(timeout=2))
PY

curl --noproxy '*' -fsS --http2 --cacert ca.crt \
    --resolve proxy.test:18443:127.0.0.1 \
    -w 'client HTTP/%{http_version}\n' 'https://proxy.test:18443/api/who'
```

- 두 HTTP 요청에서 각각 `18091`과 `18092` 백엔드의 응답을 볼 수 있다. 두 백엔드는 모두 `HTTP/1.1 /who?lang=ko`를 받는다.
- WebSocket 테스트는 프록시를 통해 메시지를 전송하고 `ping`을 돌려받는다.
- HTTPS 테스트는 `proxy.test`의 인증서를 검증하고 `client HTTP/2`를 출력한다. 백엔드 응답에는 여전히 `HTTP/1.1`이 표시된다.

실습이 끝나면 같은 터미널에서 종료한다.

```sh
nginx -p "$lab_dir/" -c nginx.conf -s quit
kill "$backend_pid"
```

**공식 문서** [websockets 서버와 클라이언트 예제](https://websockets.readthedocs.io/en/15.0.1/intro/examples.html) · [OpenSSL 인증서 확장 설정](https://docs.openssl.org/3.5/man5/x509v3_config/) · [curl 명령줄 옵션](https://curl.se/docs/manpage.html)
