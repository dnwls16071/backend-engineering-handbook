# Routing and Resilience with Istio

## 1. Istio에서 요청을 처리하는 위치

- `istiod`는 Kubernetes의 Service·Pod와 Istio 설정을 읽고 Envoy 프록시에 구성을 배포한다. Sidecar 모드에서는 앱 Pod 안의 Envoy가 해당 워크로드의 네트워크 트래픽을 처리하고, ingress gateway의 Envoy가 메시로 들어오는 요청을 처리한다. [Istio 아키텍처](https://istio.io/latest/docs/ops/deployment/architecture/)
- 이 실습은 `curl → ingress gateway의 Envoy → 선택된 Pod의 Envoy → Nginx` 경로로 요청을 보낸다. Nginx의 응답 본문은 앱 버전, `X-Lab-Pod` 응답 헤더는 응답한 Pod를 보여 준다.

| 리소스 | 설정하는 내용 | 실습 값 |
| :--- | :--- | :--- |
| Istio `Gateway` | 기존 gateway 프록시에 적용할 포트·프로토콜·호스트 | HTTP 80, `echo.example.test` |
| `VirtualService` | 요청의 호스트와 헤더를 매칭해 보낼 Service·subset을 결정 | 헤더가 있으면 `v2`, 일반 요청은 `v1` 90%·`v2` 10% |
| `DestinationRule` | 라우팅 목적지의 subset과 연결 풀·이상 엔드포인트 감지 정책 | `version` 라벨로 `v1`·`v2`를 구분 |

세 리소스 모두 `networking.istio.io/v1` API를 사용한다. Istio `Gateway`의 `selector`는 이미 설치된 gateway Pod를 찾아 리스너 설정을 적용한다. Kubernetes Gateway API의 `Gateway`는 `gateway.networking.k8s.io` 그룹의 별도 리소스다. [Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/), [VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/), [DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)

## 2. 새 Pod에 Envoy sidecar를 주입한다

빈 작업 디렉터리에서 운영 트래픽이 없는 로컬 kind 클러스터를 만든다. 예시는 Istio 1.32 계열의 sidecar 모드와 kind v0.31.0에서 제공하는 Kubernetes v1.35.0 노드 이미지를 사용한다. 컨테이너 런타임과 `kind`, `kubectl`, `curl`, 해당 Istio 릴리스의 `istioctl`을 준비한다. 별도 kubeconfig와 `kind-istio-routing-lab` 컨텍스트를 각 명령에 넘긴다. [kind Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/), [kind v0.31.0 릴리스](https://github.com/kubernetes-sigs/kind/releases/tag/v0.31.0), [Istio 지원표](https://istio.io/latest/docs/releases/supported-releases/), [Istio API로 시작하기](https://istio.io/latest/docs/setup/additional-setup/getting-started-istio-apis/)

```bash
ISTIO_LAB_KUBECONFIG="$PWD/istio-routing-lab.kubeconfig"
kind create cluster --name istio-routing-lab --kubeconfig "$ISTIO_LAB_KUBECONFIG" \
  --image kindest/node:v1.35.0@sha256:452d707d4862f52530247495d180205e029056831160e22870e37e3f6c1ac31f

lab_kubectl() {
  kubectl --kubeconfig "$ISTIO_LAB_KUBECONFIG" --context kind-istio-routing-lab "$@"
}
lab_istioctl() {
  istioctl --kubeconfig "$ISTIO_LAB_KUBECONFIG" --context kind-istio-routing-lab "$@"
}

lab_kubectl version
lab_istioctl x precheck
lab_istioctl install --set profile=demo \
  --set values.gateways.istio-ingressgateway.type=ClusterIP \
  --set values.gateways.istio-ingressgateway.autoscaleEnabled=false \
  --set values.gateways.istio-ingressgateway.replicaCount=1 \
  --set meshConfig.accessLogFile=/dev/stdout -y
lab_kubectl -n istio-system rollout status deployment/istio-ingressgateway --timeout=180s
lab_kubectl -n istio-system get service istio-ingressgateway

lab_kubectl create namespace istio-lab
lab_kubectl label namespace istio-lab istio-injection=enabled
```

gateway Service의 타입이 `ClusterIP`인지 확인한다. gateway 복제본 하나를 사용해 포트 포워딩과 프록시 관측의 대상이 일치하게 한다. 로그 설정은 뒤에서 gateway의 과부하 응답을 확인할 때 사용한다. [istioctl 설치](https://istio.io/latest/docs/setup/install/istioctl/), [Ingress gateway 차트 값](https://github.com/istio/istio/blob/master/manifests/charts/gateways/istio-ingress/values.yaml)

다음 내용을 `echo-app.yaml`로 저장한다. 두 Deployment의 Pod를 하나의 Service가 선택한다. Nginx는 ConfigMap의 템플릿을 환경 변수로 채우고, `/slow`의 정적 파일은 전송 속도를 낮춰 동시 요청이 겹치는 시간을 만든다. [Nginx 공식 이미지의 템플릿](https://hub.docker.com/_/nginx/), [Nginx limit_rate](https://nginx.org/en/docs/http/ngx_http_core_module.html#limit_rate)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: echo-content
  namespace: istio-lab
data:
  default.conf.template: |
    server {
      listen 8080;
      default_type text/plain;
      add_header X-Lab-Pod $hostname always;

      location = / {
        return ${LAB_STATUS} "${LAB_VERSION}\n";
      }

      location = /ready {
        return 200 "ready\n";
      }

      location = /slow {
        alias /etc/nginx/templates/slow.txt;
        limit_rate 128;
      }
    }
  slow.txt: |
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: istio-lab
spec:
  selector:
    app: echo
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo-v1
  namespace: istio-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      workload: echo-v1
  template:
    metadata:
      labels:
        app: echo
        version: v1
        workload: echo-v1
    spec:
      containers:
        - name: nginx
          image: nginx:stable-alpine
          env:
            - name: LAB_VERSION
              value: v1
            - name: LAB_STATUS
              value: "200"
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /ready
              port: http
          volumeMounts:
            - name: content
              mountPath: /etc/nginx/templates
              readOnly: true
      volumes:
        - name: content
          configMap:
            name: echo-content
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo-v2
  namespace: istio-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      workload: echo-v2
  template:
    metadata:
      labels:
        app: echo
        version: v2
        workload: echo-v2
    spec:
      containers:
        - name: nginx
          image: nginx:stable-alpine
          env:
            - name: LAB_VERSION
              value: v2
            - name: LAB_STATUS
              value: "200"
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /ready
              port: http
          volumeMounts:
            - name: content
              mountPath: /etc/nginx/templates
              readOnly: true
      volumes:
        - name: content
          configMap:
            name: echo-content
```

```bash
lab_kubectl apply -f echo-app.yaml
lab_kubectl -n istio-lab rollout status deployment/echo-v1 --timeout=120s
lab_kubectl -n istio-lab rollout status deployment/echo-v2 --timeout=120s
lab_kubectl -n istio-lab get pods -l app=echo -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\t"}{.spec.initContainers[*].name}{"\n"}{end}'
```

두 Pod의 컨테이너 목록에서 `nginx`와 `istio-proxy`를 확인한다. Istio의 admission webhook은 Pod가 생성될 때 프록시를 주입한다. 네임스페이스 레이블을 기존 Deployment의 Pod에 적용하려면 레이블을 먼저 붙이고 해당 Deployment를 롤아웃해 새 Pod를 만든다. [Sidecar 자동 주입](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

## 3. ingress 호스트를 Service의 subset에 연결한다

다음 내용을 `echo-routing.yaml`로 저장한다. `Gateway.spec.selector`는 demo 프로필의 `istio=ingressgateway` Pod에 매칭된다. 기본 설치의 Gateway 선택자는 네임스페이스를 넘어 gateway Pod를 선택할 수 있다. `VirtualService.hosts`는 요청의 HTTP 호스트이고, `route.destination.host`와 `DestinationRule.host`는 내부 Service의 DNS 이름이다. 예시는 기본 클러스터 도메인인 `cluster.local`을 사용한다. [Gateway의 선택자 범위](https://istio.io/latest/docs/reference/config/networking/gateway/#Gateway), [Istio ingress 설정](https://istio.io/latest/docs/tasks/traffic-management/ingress/ingress-control/)

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: echo
  namespace: istio-lab
spec:
  host: echo.istio-lab.svc.cluster.local
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: echo
  namespace: istio-lab
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - echo.example.test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: echo
  namespace: istio-lab
spec:
  hosts:
    - echo.example.test
  gateways:
    - echo
  http:
    - name: force-v2
      match:
        - headers:
            x-lab-canary:
              exact: v2
      retries:
        attempts: 0
      route:
        - destination:
            host: echo.istio-lab.svc.cluster.local
            subset: v2
    - name: weighted
      route:
        - destination:
            host: echo.istio-lab.svc.cluster.local
            subset: v1
          weight: 90
        - destination:
            host: echo.istio-lab.svc.cluster.local
            subset: v2
          weight: 10
```

```bash
lab_kubectl apply -f echo-routing.yaml
lab_istioctl analyze -n istio-lab
```

같은 작업 디렉터리의 두 번째 터미널에서 포트 포워딩을 열어 둔다.

```bash
kubectl --kubeconfig "$PWD/istio-routing-lab.kubeconfig" --context kind-istio-routing-lab \
  -n istio-system port-forward --address 127.0.0.1 svc/istio-ingressgateway 18080:80
```

이후 명령은 셸 함수를 정의한 첫 번째 터미널에서 실행한다. `127.0.0.1:18080`에 연결하되 `Host`에 `echo.example.test`를 지정한다. 이렇게 하면 DNS를 설정하지 않고도 gateway의 호스트 매칭을 확인할 수 있다. 이 `VirtualService`는 `gateways`에 지정한 ingress에 적용되므로 시험 요청도 포트 포워딩을 거친다. [kubectl port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/), [VirtualService의 gateways](https://istio.io/latest/docs/reference/config/networking/virtual-service/#VirtualService)

```bash
curl -si -H 'Host: echo.example.test' http://127.0.0.1:18080/
```

## 4. 카나리 비율과 헤더의 우선순위를 확인한다

`VirtualService.http`는 위에서 아래로 평가하며 **처음 일치한 규칙**을 적용한다. `x-lab-canary: v2`는 첫 규칙에서 `v2`로 고정된다. 헤더가 없거나 값이 다르면 마지막 규칙에서 90 대 10의 가중치를 적용한다. 가중치는 요청 분배 비율이므로 요청 횟수가 적을수록 관측 비율의 변동이 크다. [HTTP 규칙 순서](https://istio.io/latest/docs/reference/config/networking/virtual-service/#VirtualService), [트래픽 가중치 전환](https://istio.io/latest/docs/tasks/traffic-management/traffic-shifting/)

```bash
for i in $(seq 1 100); do
  curl -fsS -H 'Host: echo.example.test' http://127.0.0.1:18080/
done | sort | uniq -c

for i in $(seq 1 5); do
  curl -fsS -H 'Host: echo.example.test' -H 'x-lab-canary: v2' http://127.0.0.1:18080/
done
```

첫 명령에서 `v1`이 다수이고 `v2`가 일부인지 확인한다. 두 번째 명령은 매번 `v2`를 반환한다. 버전 비율을 되돌릴 때는 `weighted` 규칙을 `100/0`으로 바꾸고, 헤더를 붙인 요청까지 모두 `v1`으로 되돌리려면 `force-v2` 규칙도 제거한다.

## 5. 테스트 헤더가 있는 호출에만 장애를 주입한다

전용 실습의 gateway에서 `x-lab-fault: abort`는 HTTP 503을 반환하고, `x-lab-fault: delay`는 2초 기다린 뒤 `v1`으로 전달한다. 각 동작은 해당 헤더에 매칭된 요청의 100%에 적용된다. 장애 규칙을 헤더 카나리와 기본 분배 앞에 삽입하므로 두 헤더를 함께 보내면 장애 규칙이 우선한다. [Istio fault injection](https://istio.io/latest/docs/tasks/traffic-management/fault-injection/)

```bash
lab_kubectl -n istio-lab patch virtualservice echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/http/0/name
  value: force-v2
- op: add
  path: /spec/http/0
  value:
    name: fault-delay
    match:
      - headers:
          x-lab-fault:
            exact: delay
    fault:
      delay:
        percentage:
          value: 100
        fixedDelay: 2s
    route:
      - destination:
          host: echo.istio-lab.svc.cluster.local
          subset: v1
- op: add
  path: /spec/http/0
  value:
    name: fault-abort
    match:
      - headers:
          x-lab-fault:
            exact: abort
    fault:
      abort:
        percentage:
          value: 100
        httpStatus: 503
    route:
      - destination:
          host: echo.istio-lab.svc.cluster.local
          subset: v1
YAML

curl -si -H 'Host: echo.example.test' -H 'x-lab-fault: abort' http://127.0.0.1:18080/
curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' \
  -H 'Host: echo.example.test' -H 'x-lab-fault: delay' http://127.0.0.1:18080/
curl -si -H 'Host: echo.example.test' -H 'x-lab-canary: v2' http://127.0.0.1:18080/
```

`abort` 응답에는 gateway가 생성한 503이 보이고, 백엔드에서 추가하는 `X-Lab-Pod` 헤더는 빠진다. `delay`는 약 2초가 추가된 200으로 관측되며 마지막 호출은 정상적으로 `v2`를 반환한다. 다음 실습에 들어가기 전에 장애 규칙을 제거한 뒤 동일한 장애 헤더의 호출도 200으로 복구되는지 확인한다.

```bash
lab_kubectl -n istio-lab patch virtualservice echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/http/0/name
  value: fault-abort
- op: test
  path: /spec/http/1/name
  value: fault-delay
- op: remove
  path: /spec/http/1
- op: remove
  path: /spec/http/0
YAML
curl -si -H 'Host: echo.example.test' -H 'x-lab-fault: abort' http://127.0.0.1:18080/
```

## 6. 연결 풀 제한으로 동시 호출을 제어한다

`DestinationRule`의 `v2` subset에만 연결 풀 정책을 붙인다. `maxConnections`는 업스트림 연결, `http1MaxPendingRequests`는 준비된 연결을 기다리는 요청, `http2MaxRequests`는 처리 중인 HTTP 요청에 적용하는 한도다. `http2MaxRequests`는 HTTP/1.1과 HTTP/2에 적용된다. Envoy는 각 프록시의 업스트림 클러스터와 우선순위별로 한도를 계산하므로 프록시 수나 선택 가능한 엔드포인트 수에 따라 관측값이 달라진다. [Istio 연결 풀 설정](https://istio.io/latest/docs/reference/config/networking/destination-rule/#ConnectionPoolSettings), [Envoy circuit breaking](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)

```bash
lab_kubectl -n istio-lab patch destinationrule echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/subsets/1/name
  value: v2
- op: add
  path: /spec/subsets/1/trafficPolicy
  value:
    connectionPool:
      tcp:
        maxConnections: 1
      http:
        http1MaxPendingRequests: 1
        http2MaxRequests: 1
YAML

curl -sS --max-time 15 -o /dev/null -w '%{http_code} %{time_total}s\n' \
  -H 'Host: echo.example.test' -H 'x-lab-canary: v2' http://127.0.0.1:18080/slow

seq 1 16 | xargs -P 8 -n 1 sh -c '
  curl -sS --max-time 15 -o /dev/null -w "%{http_code}\n" \
    -H "Host: echo.example.test" -H "x-lab-canary: v2" "http://127.0.0.1:18080/slow?run=$1"
' sh | sort | uniq -c

lab_kubectl -n istio-system logs deployment/istio-ingressgateway -c istio-proxy --since=2m |
  grep -E '"/slow\?|upstream_reset_before_response_started'
```

단일 호출에서 응답이 완료되는 시간과 HTTP 200을 먼저 확인한다. 병렬 호출에서는 `/slow`를 처리하는 동안 한도를 초과한 일부 요청이 503으로 빠르게 실패할 수 있다. gateway 로그의 `UO`는 업스트림 과부하를 나타낸다. 200만 보이면 `v2`로 고정하는 헤더, 요청 동시성, gateway의 설정 전파를 확인한 뒤 다시 측정한다. 병렬 실행이 끝나면 단일 호출을 다시 보내 200을 확인한다. [Istio circuit breaking 실습](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/), [Envoy 응답 플래그](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage#command-operators)

## 7. 오류가 반복되는 엔드포인트를 일시적으로 제외한다

`outlierDetection`은 실제 호출의 실패를 보고 해당 엔드포인트를 일시적으로 로드밸런싱 풀에서 제외한다. 같은 subset에 오류를 내는 엔드포인트와 트래픽을 계속 처리할 정상 엔드포인트가 있어야 전후 차이를 관측할 수 있다. 여기서는 `v2`의 정상 Pod를 유지하고, 동일한 subset에 속하면서 `/`에 500을 반환하는 실습용 Pod를 추가한다. `/ready`는 200을 반환하므로 Kubernetes는 두 Pod를 모두 준비 상태로 다룬다. [Istio outlier detection](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection), [Envoy outlier detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)

다음 내용을 `echo-v2-bad.yaml`로 저장한다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo-v2-bad
  namespace: istio-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      workload: echo-v2-bad
  template:
    metadata:
      labels:
        app: echo
        version: v2
        workload: echo-v2-bad
    spec:
      containers:
        - name: nginx
          image: nginx:stable-alpine
          env:
            - name: LAB_VERSION
              value: v2
            - name: LAB_STATUS
              value: "500"
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /ready
              port: http
          volumeMounts:
            - name: content
              mountPath: /etc/nginx/templates
              readOnly: true
      volumes:
        - name: content
          configMap:
            name: echo-content
```

먼저 연결 풀 제한을 제거하고 라운드 로빈으로 두 Pod가 선택되는지 확인한다. `X-Lab-Pod`를 보면 200과 500이 각각 어느 Pod에서 돌아왔는지 알 수 있다.

```bash
lab_kubectl -n istio-lab patch destinationrule echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/subsets/1/name
  value: v2
- op: replace
  path: /spec/subsets/1/trafficPolicy
  value:
    loadBalancer:
      simple: ROUND_ROBIN
YAML
lab_kubectl apply -f echo-v2-bad.yaml
lab_kubectl -n istio-lab rollout status deployment/echo-v2-bad --timeout=120s
lab_kubectl -n istio-lab get pods -l 'app=echo,version=v2' -o wide

for i in $(seq 1 8); do
  curl -sS -D - -o /dev/null -H 'Host: echo.example.test' \
    -H 'x-lab-canary: v2' http://127.0.0.1:18080/ | awk 'tolower($0) ~ /^(http\/|x-lab-pod:)/'
done
```

이제 한 엔드포인트가 두 번 연속 5xx를 반환하면 30초간 제외하도록 설정한다. 엔드포인트가 두 개이고 `maxEjectionPercent`가 50%이므로 최대 한 개를 제외할 수 있다. `minHealthPercent: 0`은 건강한 엔드포인트 비율에 따른 감지 중단 조건을 해제한다.

```bash
lab_kubectl -n istio-lab patch destinationrule echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/subsets/1/name
  value: v2
- op: add
  path: /spec/subsets/1/trafficPolicy/outlierDetection
  value:
    consecutive5xxErrors: 2
    interval: 2s
    baseEjectionTime: 30s
    maxEjectionPercent: 50
    minHealthPercent: 0
YAML

for i in $(seq 1 12); do
  curl -sS -D - -o /dev/null -H 'Host: echo.example.test' \
    -H 'x-lab-canary: v2' http://127.0.0.1:18080/ | awk 'tolower($0) ~ /^(http\/|x-lab-pod:)/'
  sleep 0.2
done

GATEWAY_POD=$(lab_kubectl -n istio-system get pods -l istio=ingressgateway \
  -o jsonpath='{.items[0].metadata.name}')
lab_istioctl proxy-config endpoints "$GATEWAY_POD" -n istio-system \
  --cluster 'outbound|80|v2|echo.istio-lab.svc.cluster.local'
```

초기에 500이 관측되다가 제외가 적용되면 정상 Pod의 200이 이어진다. 그때 `OUTLIER CHECK` 열을 앞서 조회한 Pod IP와 대조한다. 이 상태는 요청을 처리한 gateway 프록시 기준이다. 실패가 계속되는 Pod는 제외 시간이 지나면 다시 선택될 수 있고, 이후 다시 제외될 수 있다. [프록시의 엔드포인트 확인](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/), [엔드포인트 제외 기간](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)

실습을 이어가려면 오류 Pod를 삭제하고 `v2`의 실습용 정책을 제거한다. 헤더를 붙인 요청이 다시 200으로 응답하는지 확인한다.

```bash
lab_kubectl -n istio-lab delete deployment echo-v2-bad
lab_kubectl -n istio-lab patch destinationrule echo --type=json --patch-file /dev/stdin <<'YAML'
- op: test
  path: /spec/subsets/1/name
  value: v2
- op: remove
  path: /spec/subsets/1/trafficPolicy
YAML
curl -si -H 'Host: echo.example.test' -H 'x-lab-canary: v2' http://127.0.0.1:18080/
```

실습을 마쳤다면 포트 포워딩 터미널에서 Ctrl+C를 누르고, 이 문서에서 만든 `istio-lab` 네임스페이스를 삭제한다.

```bash
lab_kubectl delete namespace istio-lab
```

위에서 만든 로컬 클러스터도 정리하려면 같은 실습 이름과 kubeconfig를 지정해 삭제한다. [kind 클러스터 삭제](https://kind.sigs.k8s.io/docs/user/quick-start/#deleting-a-cluster)

```bash
kind delete cluster --name istio-routing-lab --kubeconfig "$ISTIO_LAB_KUBECONFIG"
```
