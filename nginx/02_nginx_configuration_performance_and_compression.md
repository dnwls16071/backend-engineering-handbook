# NGINX Configuration, Performance, and Compression

NGINX 설정은 지시어를 어느 블록에 두느냐에 따라 적용 범위가 달라진다. 설정 구조와 상속을 이해한 뒤, 정적 파일을 제공하는 서버에 공통 설정과 gzip을 추가해 응답 헤더와 다운로드 크기를 비교한다.

## 1. 설정 블록과 지시어 문법

| 컨텍스트 | 적용 범위 | 예시 |
| --- | --- | --- |
| `main` | 블록 바깥의 최상위 설정 | `worker_processes`, `pid` |
| `events` | 워커의 연결 처리 | `worker_connections` |
| `http` | HTTP 서버 전체의 공통 설정 | `sendfile`, `gzip` |
| `server` | 개별 HTTP 가상 서버 | `listen`, `server_name` |
| `location` | 선택된 서버 안에서 요청 URI에 따라 적용되는 설정 | `root`, `try_files` |

단순 지시어는 세미콜론으로 끝나고, 블록 지시어는 중괄호 안에 설정을 담는다. 일반 HTTP 요청은 먼저 `server`를 고르고, 그 안에서 URI에 맞는 `location`을 찾는다. 예를 들어 `location = /health`의 `=`는 URI 경로가 정확히 일치할 때 적용한다는 뜻이다. 지시어를 추가할 때는 공식 문서의 `Context` 항목에서 허용되는 위치를 확인한다.

**공식 문서** [NGINX 설정 파일 구조](https://nginx.org/en/docs/beginners_guide.html#conf_structure) · [HTTP server와 location](https://nginx.org/en/docs/http/ngx_http_core_module.html#location)

## 2. 상속과 덮어쓰기

상속 규칙은 지시어마다 다르다. 예를 들어 `gzip on;`을 `http`에 두고 특정 `location`에 `gzip off;`를 지정하면 그 경로만 압축하지 않는다.

`add_header`는 기본 규칙에서 목록 단위로 동작한다. 상위 `server`에 `add_header X-Lab-Site demo;`가 있어도, 하위 `location`에 `add_header X-Lab-Check ready;`를 하나 선언하면 그 경로에는 `X-Lab-Check`만 붙는다. 두 헤더가 모두 필요하면 하위 블록에 공통 헤더도 선언한다. NGINX 1.29.3부터는 `add_header_inherit merge;`를 사용해 상위 헤더 목록을 합칠 수 있다.

**공식 문서** [gzip 지시어](https://nginx.org/en/docs/http/ngx_http_gzip_module.html#gzip) · [add_header 상속 규칙](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header) · [add_header_inherit](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header_inherit)

## 3. include로 설정 파일 나누기

| 파일 | 역할 |
| --- | --- |
| `nginx.conf` | 프로세스, 연결 처리, HTTP 공통 설정 |
| `conf.d/site.conf` | 포트, 문서 루트, 경로별 응답을 정하는 가상 서버 |
| `snippets/gzip.conf` | 서버 간에 재사용할 수 있는 압축 설정 조각 |

`include conf.d/*.conf;`는 패턴에 맞는 설정 파일을 읽는다. 포함한 파일의 지시어는 `include`를 둔 위치의 컨텍스트에서 유효해야 한다. 예를 들어 `server { ... }`를 담은 파일은 `http` 안에서 읽고, 공통 설정 조각은 해당 지시어를 사용할 수 있는 블록에서 읽는다. `nginx -T`를 실행하면 설정 검사와 함께 읽어들인 설정을 출력한다.

**공식 문서** [include 지시어](https://nginx.org/en/docs/ngx_core_module.html#include) · [NGINX 명령줄 옵션](https://nginx.org/en/docs/switches.html)

## 4. 워커 수와 연결 한도 설정

| 지시어 | 조정할 때 볼 항목 |
| --- | --- |
| `worker_processes auto` | NGINX가 감지한 CPU에 맞춰 워커 수를 정하는 출발점이다. 변경 전후에 CPU 사용량과 처리량을 비교한다. |
| `worker_connections 1024` | 워커 하나가 동시에 열 수 있는 연결 수의 예시다. 클라이언트와 업스트림 연결을 모두 포함한다. |
| `worker_rlimit_nofile` | 워커의 열린 파일 디스크립터 한도를 조정한다. 연결 소켓과 로그 파일도 디스크립터를 사용하므로 OS 및 서비스의 한도를 함께 확인한다. |

`워커 수 × worker_connections`는 연결 슬롯의 이론적인 합계다. 예를 들어 프록시가 요청을 처리하면서 클라이언트 소켓과 업스트림 소켓을 함께 열면 한 요청에 두 연결 슬롯을 쓸 수 있다. 설정을 조정할 때는 같은 요청 패턴에서 초당 요청 수, p95 응답 시간, 오류율과 CPU 사용량을 비교한다.

**공식 문서** [worker_processes](https://nginx.org/en/docs/ngx_core_module.html#worker_processes) · [worker_connections](https://nginx.org/en/docs/ngx_core_module.html#worker_connections) · [worker_rlimit_nofile](https://nginx.org/en/docs/ngx_core_module.html#worker_rlimit_nofile)

## 5. 기본 설정

NGINX가 설치된 환경에서 다음 블록을 실행한다. 임시 디렉터리에서 설정과 로그를 관리하고 `127.0.0.1:18081`에만 바인딩한다. 포트가 사용 중이면 설정과 요청 URL에서 포트를 함께 바꾼다.

```sh
lab_dir="$(mktemp -d)"
cd "$lab_dir" || exit 1
mkdir -p conf.d snippets html

cat > nginx.conf <<'CONF'
worker_processes auto;
pid nginx.pid;
error_log error.log warn;

events {
    worker_connections 1024;
}

http {
    types {
        text/html html;
        text/css css;
    }
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 30s;

    include snippets/gzip.conf;
    include conf.d/*.conf;
}
CONF

cat > conf.d/site.conf <<'CONF'
server {
    listen 127.0.0.1:18081;
    root html;
    add_header X-Lab-Site demo;

    location = /health {
        add_header X-Lab-Check ready;
        return 200 "ok\n";
    }
}
CONF

printf 'gzip off;\n' > snippets/gzip.conf
awk 'BEGIN {
    for (i = 0; i < 200; i++)
        printf ".item-%d { color: #333; padding: 8px; }\n", i
}' > html/app.css

nginx -p "$lab_dir/" -c nginx.conf -t &&
    nginx -p "$lab_dir/" -c nginx.conf
```

`sendfile on;`은 정적 파일을 전송할 때 OS의 `sendfile()` 사용을 활성화한다. `keepalive_timeout 30s;`는 요청 처리가 끝난 뒤 클라이언트 연결을 재사용할 수 있도록 유휴 상태로 유지하는 시간이다. 이 값은 실습의 시작점이며, 운영에서는 연결 재사용률과 유휴 연결 수를 보고 조정한다.

```sh
curl -fsS -D - -o /dev/null http://127.0.0.1:18081/app.css
curl -fsS -D - -o /dev/null http://127.0.0.1:18081/health
```

`/app.css`에는 `X-Lab-Site: demo`가, `/health`에는 `X-Lab-Check: ready`가 나온다. CSS 응답의 `Content-Type: text/css`도 확인한다. gzip은 응답의 MIME 타입을 기준으로 압축 대상을 선택한다. 실습의 `types` 블록에는 HTML과 CSS만 있다. 더 많은 파일 형식을 서비스할 때는 패키지에 포함된 `mime.types` 파일을 읽도록 설정한다.

**공식 문서** [sendfile](https://nginx.org/en/docs/http/ngx_http_core_module.html#sendfile) · [keepalive_timeout](https://nginx.org/en/docs/http/ngx_http_core_module.html#keepalive_timeout) · [types](https://nginx.org/en/docs/http/ngx_http_core_module.html#types)

## 6. gzip 설정과 전송량 비교

같은 터미널에서 압축 설정 파일을 교체하고 설정 검사를 통과하면 리로드한다. 새 설정이 반영된 뒤, 동일한 파일을 압축 없이 한 번, gzip을 사용해 한 번 다운로드한다.

```sh
cat > snippets/gzip.conf <<'CONF'
gzip on;
gzip_comp_level 3;
gzip_min_length 1024;
gzip_types text/plain text/css application/javascript application/json image/svg+xml;
gzip_vary on;
CONF

nginx -p "$lab_dir/" -c nginx.conf -t &&
    nginx -p "$lab_dir/" -c nginx.conf -s reload
```

| 설정 | 의미 |
| --- | --- |
| `gzip_comp_level 3` | 실습에 사용할 압축 레벨이다. 레벨을 높일 때는 절약한 바이트와 추가 CPU 비용을 함께 측정한다. |
| `gzip_min_length 1024` | 응답의 `Content-Length`가 있을 때 적용하는 최소 길이다. |
| `gzip_types` | `text/html` 외에 추가로 압축할 MIME 타입을 지정한다. |
| `gzip_vary on` | `Vary: Accept-Encoding`을 추가해 캐시가 요청의 인코딩 지원 여부에 따라 응답을 구분할 수 있게 한다. |

```sh
url="http://127.0.0.1:18081/app.css"

curl -fsS -H 'Accept-Encoding: identity' -o /dev/null \
    -w 'uncompressed: %{size_download} bytes\n' "$url"

curl -fsS -H 'Accept-Encoding: gzip' -D - -o /dev/null \
    -w 'gzip: %{size_download} bytes\n' "$url"
```

두 번째 요청에서 `Content-Encoding: gzip`과 `Vary: Accept-Encoding`을 확인하고 본문 전송량을 비교한다. 헤더가 아직 나오지 않으면 리로드 후 새 워커가 응답할 때 다시 요청한다. 로컬 NGINX 1.31.3에서 예제 CSS는 8,090바이트에서 538바이트로 줄었다. 동일한 텍스트가 반복되는 예제 파일은 압축률이 높으므로 실제 성능을 평가할 때는 서비스에서 제공하는 파일로 다시 측정한다.

실습을 마치면 `nginx -p "$lab_dir/" -c nginx.conf -s quit`으로 실습 인스턴스를 종료한다.

**공식 문서** [NGINX gzip 모듈](https://nginx.org/en/docs/http/ngx_http_gzip_module.html) · [설정 리로드 동작](https://nginx.org/en/docs/control.html#reconfiguration)
