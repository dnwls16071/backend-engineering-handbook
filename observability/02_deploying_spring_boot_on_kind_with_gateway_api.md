# Deploying Spring Boot on kind with Gateway API

## 1. Compose의 서비스 구성을 kind로 옮긴다

Compose는 호스트의 Docker에서 앱과 의존 서비스를 컨테이너로 실행한다. kind는 Docker 컨테이너를 Kubernetes 노드로 사용하며, 각 노드의 kubelet과 containerd가 Pod를 실행한다. 호스트에서 빌드한 이미지가 kind 노드에 필요하면 `kind load docker-image`로 가져온다. [컨테이너 실행 구조](../kubernetes/01_container.md), [kind Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/)

| Kubernetes 리소스 | SNS 실습에서 하는 일 |
| :--- | :--- |
| Namespace | `sns` 이름 아래에 앱 리소스를 모은다. |
| Deployment·Pod | Deployment가 이미지, 실행 설정, 복제 수를 선언하고 Pod에서 컨테이너를 실행한다. |
| Probe | kubelet이 시작 완료, 재시작 필요 여부와 요청 처리 준비 상태를 판단한다. |
| Secret | DB 비밀번호와 S3 인증 값을 필요한 컨테이너에 전달한다. |
| Service | Pod가 교체되어도 같은 DNS 이름과 포트로 접속할 수 있게 한다. |
| PV·PVC | PV는 실제 스토리지를 표현하고, PVC는 Pod에 필요한 저장 공간을 요청한다. |

같은 Namespace에서는 Compose 때와 같이 `postgres:5432`, `redis:6379`, `rustfs:9000`을 사용한다. Service의 selector는 Pod 라벨과 일치해야 한다. 외부 요청은 Traefik을 거쳐 앱 Service로 들어오고, 의존 서비스는 `ClusterIP`로 클러스터 내부에 둔다. [Kubernetes 오브젝트](../kubernetes/03_object.md), [Secret](../kubernetes/05_understanding_k8s_via_app_features_configmap_secret.md), [Service](../kubernetes/10_service.md), [PV와 PVC](../kubernetes/12_pv_and_pvc.md)

```bash
kind create cluster --name sns --wait 120s
kubectl config use-context kind-sns
kubectl get nodes -o wide
kind load docker-image sns-api:local --name sns

kubectl create namespace sns
kubectl -n sns create secret generic sns-credentials \
  --from-env-file=.env.local --dry-run=client -o yaml |
  kubectl apply --server-side -f -
kubectl get storageclass
```

`sns-api:local`과 `.env.local`은 앞 편에서 준비한다. 두 도구에서 같은 환경 파일을 읽을 수 있도록 파일에 `KEY=value` 형식의 값만 둔다. Secret의 Base64 표현은 인코딩이고, Secret 조회 권한은 RBAC로 제한한다. 이 예시는 PVC를 동적으로 프로비저닝할 기본 StorageClass가 있는 클러스터에서 동작한다. [Jib과 Compose 실습](01_containerizing_spring_boot_with_jib_and_docker_compose.md), [Kubernetes Secret](https://kubernetes.io/docs/concepts/configuration/secret/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

## 2. PostgreSQL·Redis·RustFS 실행하기

아래를 `k8s/dependencies.yaml`로 저장한다. 단일 인스턴스 실습에서는 PostgreSQL·RustFS가 각자의 PVC를 마운트한다. `Recreate`는 Deployment를 갱신할 때 기존 Pod를 종료한 뒤 새 Pod를 시작하므로 갱신 중 잠시 연결이 끊긴다. 운영에서 인스턴스마다 고유한 저장 공간이나 DB 복제가 필요하면 StatefulSet이나 해당 서비스의 운영 방식을 검토한다. [Kubernetes StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/), [PostgreSQL 공식 이미지](https://hub.docker.com/_/postgres), [RustFS Kubernetes 설치](https://docs.rustfs.com/en/installation/cloud-native)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests: {storage: 1Gi}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  strategy: {type: Recreate}
  selector:
    matchLabels: {app: postgres}
  template:
    metadata:
      labels: {app: postgres}
    spec:
      containers:
        - name: postgres
          image: postgres:17
          env:
            - {name: POSTGRES_DB, value: sns}
            - {name: POSTGRES_USER, value: sns}
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: POSTGRES_PASSWORD}
          readinessProbe:
            exec:
              command: [pg_isready, -h, "127.0.0.1", -U, sns, -d, sns]
          volumeMounts:
            - {name: data, mountPath: /var/lib/postgresql/data}
      volumes:
        - name: data
          persistentVolumeClaim: {claimName: postgres-data}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector: {app: postgres}
  ports:
    - {port: 5432}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  selector:
    matchLabels: {app: redis}
  template:
    metadata:
      labels: {app: redis}
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          readinessProbe:
            exec:
              command: [redis-cli, ping]
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector: {app: redis}
  ports:
    - {port: 6379}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rustfs-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests: {storage: 2Gi}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rustfs
spec:
  strategy: {type: Recreate}
  selector:
    matchLabels: {app: rustfs}
  template:
    metadata:
      labels: {app: rustfs}
    spec:
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
        - name: rustfs
          image: rustfs/rustfs:1.0.3
          args: ["/data"]
          env:
            - name: RUSTFS_ACCESS_KEY
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: S3_ACCESS_KEY}
            - name: RUSTFS_SECRET_KEY
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: S3_SECRET_KEY}
          readinessProbe:
            httpGet: {path: /health, port: 9000}
          volumeMounts:
            - {name: data, mountPath: /data}
      volumes:
        - name: data
          persistentVolumeClaim: {claimName: rustfs-data}
---
apiVersion: v1
kind: Service
metadata:
  name: rustfs
spec:
  selector: {app: rustfs}
  ports:
    - {port: 9000}
```

```bash
kubectl -n sns apply -f k8s/dependencies.yaml
kubectl -n sns rollout status deploy/postgres --timeout=120s
kubectl -n sns rollout status deploy/redis --timeout=120s
kubectl -n sns rollout status deploy/rustfs --timeout=120s
kubectl -n sns get pvc,pod,svc
```

`PVC`가 `Pending`이면 동적 프로비저닝과 Pod 스케줄링 이벤트를 확인한다. RustFS가 `Permission denied`를 기록하면 스토리지에서 `fsGroup`을 적용하는지와 UID 10001이 `/data`에 쓸 수 있는지 확인한다. `pg_isready`와 RustFS `/health` 이후에는 앱에서 실제로 인증하고 데이터를 읽고 쓰는 흐름을 확인한다. [Kubernetes 볼륨 권한](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/), [RustFS Docker 설치](https://docs.rustfs.com/en/installation/container/docker)

## 3. Spring Boot Deployment와 Service 연결하기

아래 두 리소스를 `k8s/sns-deployment.yaml`, `k8s/sns-service.yaml`로 각각 저장한다. 앱 이미지를 바꾸면 Deployment의 Pod 템플릿이 변경되어 롤아웃이 시작된다. 로컬 실습에서는 새 이미지를 빌드할 때 새 태그를 지정하고, 같은 태그를 `kind load docker-image`와 Deployment에 사용한다. [kind 이미지 로드](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster), [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sns-api
spec:
  replicas: 1
  selector:
    matchLabels: {app: sns-api}
  template:
    metadata:
      labels: {app: sns-api}
    spec:
      containers:
        - name: sns-api
          image: sns-api:local
          imagePullPolicy: IfNotPresent
          ports:
            - {name: http, containerPort: 8080}
          env:
            - {name: SPRING_DATASOURCE_URL, value: "jdbc:postgresql://postgres:5432/sns"}
            - {name: SPRING_DATASOURCE_USERNAME, value: sns}
            - name: SPRING_DATASOURCE_PASSWORD
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: POSTGRES_PASSWORD}
            - {name: SPRING_DATA_REDIS_HOST, value: redis}
            - {name: S3_ENDPOINT, value: "http://rustfs:9000"}
            - name: S3_ACCESS_KEY
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: S3_ACCESS_KEY}
            - name: S3_SECRET_KEY
              valueFrom:
                secretKeyRef: {name: sns-credentials, key: S3_SECRET_KEY}
            - {name: MANAGEMENT_ENDPOINT_HEALTH_PROBES_ENABLED, value: "true"}
          startupProbe:
            httpGet: {path: /actuator/health/liveness, port: http}
            periodSeconds: 2
            failureThreshold: 30
          livenessProbe:
            httpGet: {path: /actuator/health/liveness, port: http}
          readinessProbe:
            httpGet: {path: /actuator/health/readiness, port: http}
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sns-api
spec:
  selector: {app: sns-api}
  ports:
    - {name: http, port: 8080, targetPort: http}
```

```bash
kubectl -n sns apply -f k8s/sns-deployment.yaml -f k8s/sns-service.yaml
kubectl -n sns rollout status deploy/sns-api --timeout=120s
kubectl -n sns get endpointslice -l kubernetes.io/service-name=sns-api
```

startup probe가 성공하면 kubelet이 liveness·readiness probe를 시작한다. liveness 실패가 임계치를 넘으면 컨테이너를 재시작하고, readiness 실패는 해당 Pod를 Service의 일반 요청 대상에서 제외한다. 공용 PostgreSQL이나 Redis 장애 때 앱이 일제히 재시작하지 않도록 liveness는 앱 자체 상태에 한정한다. [Probe 실습](../kubernetes/04_probe.md), [Spring Boot Actuator](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.kubernetes-probes), [Kubernetes Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

## 4. Traefik Gateway와 HTTPRoute로 API 요청 연결하기

GatewayClass는 관리할 컨트롤러를, Gateway는 요청을 받을 리스너를, HTTPRoute는 호스트·경로와 백엔드 Service의 연결을 선언한다. Gateway API CRD를 설치한 뒤 `k8s/traefik-values.yaml`을 사용해 `traefik` Namespace에 컨트롤러를 설치하고 `sns` Namespace에 `sns-gateway`를 만든다. HTTPRoute도 `sns`에 두어 같은 Namespace의 리스너에 연결한다. [Ingress와 라우팅](../kubernetes/11_ingress.md), [Gateway API 시작 가이드](https://gateway-api.sigs.k8s.io/guides/getting-started/), [Traefik Helm Chart 값](https://github.com/traefik/traefik-helm-chart/blob/v42.4.1/traefik/values.yaml)

```yaml
providers:
  kubernetesGateway:
    enabled: true
gateway:
  name: sns-gateway
  namespace: sns
service:
  type: ClusterIP
```

```bash
kubectl apply --server-side -f \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml
kubectl wait --for=condition=Established crd/httproutes.gateway.networking.k8s.io --timeout=90s
helm upgrade --install traefik traefik \
  --repo https://traefik.github.io/charts --version 42.4.1 \
  --namespace traefik --create-namespace \
  -f k8s/traefik-values.yaml --wait
```

아래를 `k8s/sns-route.yaml`에 저장한다. `web`은 Helm 차트에서 만든 HTTP 리스너 이름이고 `8080`은 `sns-api` Service의 포트이다. 예시는 SNS 앱이 `GET /api/posts`를 제공한다고 가정한다. [Traefik Helm Chart Gateway API 예시](https://github.com/traefik/traefik-helm-chart/blob/v42.4.1/EXAMPLES.md), [Gateway API HTTPRoute](https://gateway-api.sigs.k8s.io/reference/api-types/httproute/)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: sns-api
spec:
  parentRefs:
    - {name: sns-gateway, sectionName: web}
  hostnames: [sns.localhost]
  rules:
    - matches:
        - path: {type: PathPrefix, value: /api}
      backendRefs:
        - {name: sns-api, port: 8080}
```

```bash
kubectl -n sns apply -f k8s/sns-route.yaml
kubectl -n sns get gateway
kubectl -n sns describe httproute sns-api
kubectl -n traefik port-forward svc/traefik 8081:80
```

다른 터미널에서 `curl -fsS -H 'Host: sns.localhost' http://127.0.0.1:8081/api/posts`를 실행한다. Gateway의 `Programmed`와 HTTPRoute의 `Accepted`, `ResolvedRefs` 상태를 확인하고, 요청 오류가 발생하면 호스트·경로 매칭과 Service EndpointSlice를 차례로 살핀다. 게시글 생성과 첨부 파일 읽기·쓰기까지 확인하면 의존 서비스와 연결된 동작도 검증할 수 있다. [Gateway API 상태 조건](https://gateway-api.sigs.k8s.io/geps/gep-1364/), [GitHub Actions로 이미지 게시하기](03_building_container_ci_with_github_actions.md)
