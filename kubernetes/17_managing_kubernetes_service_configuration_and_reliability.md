# Managing Kubernetes Service Configuration and Reliability

실습 명령은 전용 로컬 Kubernetes 컨텍스트를 지정해 실행한다. 예시는 `kind-ops-lab` 컨텍스트의 Linux 노드를 사용한다. 자신의 실습 클러스터 이름에 맞춰 `KUBE_CONTEXT`를 설정한다.

```bash
KUBE_CONTEXT=kind-ops-lab
lab_kubectl() {
  kubectl --context "${KUBE_CONTEXT:?}" "$@"
}
```

## 1. Namespace로 서비스 리소스의 범위를 정한다

Namespace는 한 클러스터에서 팀이나 환경별로 리소스 이름과 관리 범위를 나누는 단위다. Pod, Deployment, Service, ConfigMap, PVC는 Namespace에 속하며, 다른 Namespace에 같은 이름의 Service를 둘 수 있다. Node, PV, StorageClass는 클러스터 범위에 속한다. Pod에서 ConfigMap과 PVC를 직접 참조할 때는 Pod와 같은 Namespace에 둔다. [Kubernetes Namespaces](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/), [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

Namespace를 생성한 직후에는 기본적으로 Namespace 사이의 Pod 통신이 가능하다. API 접근 권한에는 RBAC, Pod 간 통신에는 이를 지원하는 네트워크 플러그인과 NetworkPolicy를 적용한다. 팀별 CPU·메모리 할당량은 ResourceQuota로 관리할 수 있다. 조회할 때는 `-n service-lab`로 범위를 지정하고, 리소스 종류의 범위가 헷갈리면 `lab_kubectl api-resources --namespaced=true` 또는 `--namespaced=false`로 확인한다. [Kubernetes 멀티테넌시](https://kubernetes.io/docs/concepts/security/multi-tenancy/), [Kubernetes ResourceQuota](https://kubernetes.io/docs/concepts/policy/resource-quotas/)

## 2. ConfigMap이 변경되면 앱의 설정 읽기 방식을 확인한다

| Pod에서 사용하는 방식 | ConfigMap 변경 뒤의 동작 |
| :--- | :--- |
| `envFrom` 또는 `configMapKeyRef` | 이미 실행 중인 컨테이너의 환경변수는 처음 주입된 값을 유지한다. Deployment에서는 Pod를 교체하는 롤아웃으로 새 값을 주입한다. |
| 디렉터리로 마운트한 볼륨 | kubelet이 변경을 감지한 뒤 파일에 새 값이 반영된다. 앱이 기동 시 한 번만 읽는다면 재로딩이나 재시작이 필요하다. |
| `subPath`로 마운트한 파일 | 기존 컨테이너의 단일 파일 마운트에는 ConfigMap 변경이 전달되지 않는다. |

ConfigMap API에 새 값이 보이는 시점과 컨테이너의 파일에 보이는 시점 사이에는 kubelet 동기화 및 캐시 전파 시간이 있다. 환경변수 주입과 파일 마운트 방법은 기존 문서에서 확인할 수 있다. [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/#mounted-configmaps-are-updated-automatically), [ConfigMap과 Secret으로 실행 설정 분리하기](05_understanding_k8s_via_app_features_configmap_secret.md)

## 3. PVC의 바인딩, 동시 접근과 데이터 보존을 확인한다

Pod는 PVC를 통해 저장소를 사용한다. PVC는 용량, 접근 모드, StorageClass 등을 요청하고, PV는 해당 요청에 연결될 저장소를 표현한다. StorageClass의 프로비저너가 동적 생성을 지원하면 PVC에 맞는 저장소와 PV를 만들 수 있다. `storageClassName`을 생략한 PVC에는 기본 StorageClass가 적용될 수 있다. `WaitForFirstConsumer`인 클래스에서는 PVC를 사용하는 Pod가 생기기 전까지 PVC가 `Pending`일 수 있다. [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Kubernetes Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/), [PV와 PVC](12_pv_and_pvc.md)

| 접근 모드 | 지원되는 마운트 범위 |
| :--- | :--- |
| `ReadWriteOnce` (`RWO`) | 한 노드에서 읽기·쓰기를 허용한다. 같은 노드의 여러 Pod가 사용할 수 있다. |
| `ReadOnlyMany` (`ROX`) | 여러 노드에서 읽기 전용 마운트를 지원한다. |
| `ReadWriteMany` (`RWX`) | 여러 노드에서 읽기·쓰기 마운트를 지원한다. |
| `ReadWriteOncePod` (`RWOP`) | 클러스터 전체에서 한 Pod만 읽기·쓰기로 마운트할 수 있다. Kubernetes v1.29부터 안정 기능이며, 지원하는 CSI 드라이버가 필요하다. |

접근 모드는 PVC와 PV의 매칭에 쓰이며 실제 지원 범위는 드라이버에 따라 달라진다. 읽기 전용을 적용하려면 Pod의 마운트 설정과 저장소 권한도 확인한다. 공유 파일에 여러 Pod가 쓰는 경우 앱이 동시 쓰기의 정합성을 관리해야 한다. [Kubernetes PV 접근 모드](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), [PV·PVC, Deployment, Service, HPA로 앱 운영하기](06_understanding_k8s_via_app_features_core_resources.md)

볼륨 문제가 생기면 `lab_kubectl get pvc -n service-lab`에서 `STATUS`, `VOLUME`, `STORAGECLASS`를 확인한다. `Pending`이 지속되면 PVC와 Pod의 `describe` 이벤트에서 프로비저닝·스케줄링 실패를 확인한다. `Bound`인 경우 연결된 PV의 `persistentVolumeReclaimPolicy`를 조회한다. `Retain`은 PVC 해제 후 저장 자원을 보존하며, `Delete`는 지원되는 프로비저너에서 PV와 실제 저장소 삭제까지 이어진다. 반환 정책과 데이터 보존 계획을 먼저 확인하고, 바인딩이나 마운트 문제는 PVC를 유지한 채 진단한다. [Kubernetes PV 반환 정책](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming), [Kubernetes StorageClass 바인딩 모드](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode)

## 4. Probe로 기동, 요청 수신과 재시작 조건을 설정한다

| Probe | 확인할 상태 | 실패 기준에 도달했을 때 |
| :--- | :--- | :--- |
| `startupProbe` | 초기 기동이 끝났는가? | kubelet이 컨테이너를 종료하고 재시작 정책을 적용한다. Startup이 성공할 때까지 Readiness와 Liveness 검사를 기다린다. |
| `readinessProbe` | 새 요청을 받을 수 있는가? | Pod가 준비되지 않은 상태가 되고 일반적인 Service 트래픽의 대상에서 제외된다. 컨테이너는 계속 실행한다. |
| `livenessProbe` | 재시작으로 회복할 수 있는 장애가 발생했는가? | kubelet이 컨테이너를 종료하고 재시작 정책을 적용한다. |

일시적으로 외부 의존 서비스에 연결할 수 없을 때는 Readiness를 통해 요청 유입을 줄일 수 있다. Liveness에는 교착처럼 해당 컨테이너의 재시작으로 회복할 수 있는 상태를 사용한다. 검사 주기와 연속 실패 횟수는 기동 시간과 일시적인 응답 지연을 고려해 설정한다. Service의 `publishNotReadyAddresses`가 기본값인 경우 EndpointSlice의 `conditions.ready`로 일반 트래픽 대상 여부를 관찰할 수 있다. [Kubernetes Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/), [Kubernetes EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/#conditions), [Pod Probe 설정과 운영 예시](04_probe.md)

## 5. CPU·메모리의 requests와 limits를 관찰한다

| 설정 | CPU | 메모리 |
| :--- | :--- | :--- |
| `requests` | 노드 배치 시 스케줄러가 계산하는 CPU 양이다. `100m`은 CPU 0.1개다. | 노드 배치 시 스케줄러가 계산하는 메모리 양이다. `32Mi`는 32 MiB다. |
| `limits` | Linux에서 CPU 사용이 제한에 도달하면 CPU 실행이 제한되어 응답이 지연될 수 있다. | Linux에서 제한을 초과하면 커널이 메모리 사용량에 반응해 프로세스를 종료할 수 있다. 컨테이너의 마지막 종료 상태에 `OOMKilled`가 나타날 수 있다. |

Pod에 맞는 노드가 없다면 `lab_kubectl describe pod -n service-lab`에서 `FailedScheduling` 이벤트와 CPU·메모리 부족 메시지를 확인한다. 실행 중인 Pod의 응답이 느리다면 CPU 제한으로 인한 스로틀링과 Probe 타임아웃을 함께 살핀다. 재시작이 반복되면 `Last State`의 종료 사유와 Probe 실패 이벤트를 함께 확인한다. [Kubernetes Pod·컨테이너 자원 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

## 6. 실습에서 설정 반영과 Service 대상 변화를 확인한다

실습 클러스터에 새 `service-lab` Namespace를 만든다. 같은 이름의 Namespace가 이미 존재하면 새 로컬 실습 클러스터에서 시작한다.

```bash
lab_kubectl create namespace service-lab
```

다음을 `service-lab.yaml`에 저장한다. 같은 `MESSAGE`를 환경변수와 파일로 제공한다. 웹 서버가 약 8초 뒤 포트를 열면 Startup 검사가 성공하고, `/tmp/ready`와 `/tmp/live` 파일로 이후 두 검사의 결과를 조작할 수 있다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config
  namespace: service-lab
data:
  MESSAGE: "v1"
---
apiVersion: v1
kind: Pod
metadata:
  name: web
  namespace: service-lab
  labels:
    app: service-lab-web
spec:
  restartPolicy: Always
  containers:
    - name: web
      image: busybox:1.36.1
      imagePullPolicy: IfNotPresent
      command:
        - sh
        - -ec
        - |
          mkdir -p /tmp/site
          printf 'ok\n' > /tmp/site/index.html
          sleep 8
          touch /tmp/ready /tmp/live
          exec httpd -f -p 8080 -h /tmp/site
      ports:
        - name: http
          containerPort: 8080
      envFrom:
        - configMapRef:
            name: web-config
      volumeMounts:
        - name: config
          mountPath: /etc/service-lab
          readOnly: true
      startupProbe:
        tcpSocket:
          port: http
        periodSeconds: 2
        failureThreshold: 15
      readinessProbe:
        exec:
          command: [test, -f, /tmp/ready]
        periodSeconds: 2
        failureThreshold: 1
      livenessProbe:
        exec:
          command: [test, -f, /tmp/live]
        periodSeconds: 2
        failureThreshold: 3
      resources:
        requests:
          cpu: 50m
          memory: 16Mi
        limits:
          cpu: 200m
          memory: 32Mi
  volumes:
    - name: config
      configMap:
        name: web-config
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: service-lab
spec:
  selector:
    app: service-lab-web
  ports:
    - port: 80
      targetPort: http
```

### 컨테이너 준비 상태와 초기 설정을 확인한다

```bash
lab_kubectl create -f service-lab.yaml
lab_kubectl wait -n service-lab --for=condition=Ready pod/web --timeout=120s
lab_kubectl get pod web -n service-lab
lab_kubectl exec -n service-lab web -- printenv MESSAGE
lab_kubectl exec -n service-lab web -- cat /etc/service-lab/MESSAGE
```

기대 결과는 Pod `READY`가 `1/1`, 상태는 `Running`, 재시작 횟수는 `0`이며 두 `MESSAGE` 출력이 모두 `v1`이다. `lab_kubectl describe pod web -n service-lab`에서 `Requests`와 `Limits`의 값도 확인할 수 있다.

### ConfigMap을 바꾸고 두 주입 경로를 비교한다

```bash
lab_kubectl patch configmap web-config -n service-lab --type=merge \
  -p '{"data":{"MESSAGE":"v2"}}'
lab_kubectl exec -n service-lab web -- printenv MESSAGE
lab_kubectl exec -n service-lab web -- cat /etc/service-lab/MESSAGE
```

환경변수는 `v1`을 계속 출력한다. 파일도 처음에는 `v1`일 수 있다. kubelet이 변경을 반영할 때까지 `cat`을 다시 실행하면 `v2`를 확인할 수 있다.

### Readiness 실패와 Liveness 실패를 비교한다

```bash
lab_kubectl exec -n service-lab web -- rm /tmp/ready
lab_kubectl wait -n service-lab --for=condition=Ready=false pod/web --timeout=60s
lab_kubectl get endpointslice -n service-lab -l kubernetes.io/service-name=web \
  -o 'jsonpath={.items[*].endpoints[*].conditions.ready}{"\n"}'
lab_kubectl get pod web -n service-lab
```

EndpointSlice에 상태가 전파되면 `false`가 출력된다. Pod는 `Running`으로 표시되고 `READY`는 `0/1`, 재시작 횟수는 `0`이다. 파일을 복구하면 Pod가 다시 `1/1`이 되고 EndpointSlice의 `ready`도 `true`로 돌아온다.

```bash
lab_kubectl exec -n service-lab web -- touch /tmp/ready
lab_kubectl wait -n service-lab --for=condition=Ready pod/web --timeout=60s
lab_kubectl exec -n service-lab web -- rm /tmp/live
lab_kubectl get pod web -n service-lab -w
```

Liveness가 연속 세 번 실패하면 같은 Pod에서 컨테이너가 재시작되어 `RESTARTS`가 `1`로 증가한다. 실행 명령이 두 파일을 다시 만들고 Startup과 Readiness 검사를 통과하면 `1/1`로 돌아온다. 관찰을 마치면 `Ctrl+C`로 종료한다. [Kubernetes Probe 구성 실습](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

실습을 마치면 생성한 세 리소스를 이름으로 정리한다.

```bash
lab_kubectl delete -n service-lab pod/web service/web configmap/web-config
```

## 7. Pod를 교체한 뒤에도 PVC의 파일이 남는지 확인한다

`lab_kubectl get storageclass`에서 기본 StorageClass와 동적 프로비저너를 확인한다. 기본 클래스가 없으면 사용할 클래스 이름을 PVC의 `spec.storageClassName`에 지정한다. 아래를 `volume-lab.yaml`로 저장한다. 6절에서 만든 `service-lab`에 PVC와 테스트 Pod를 생성한다. Pod가 같은 이름으로 교체되어도 PVC는 유지된다. [Kubernetes · Persistent Volume 구성 실습](https://kubernetes.io/docs/tasks/configure-pod-container/configure-persistent-volume-storage/)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: notes-data
  namespace: service-lab
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: volume-check
  namespace: service-lab
spec:
  containers:
    - name: reader
      image: busybox:1.36.1
      command: ["sleep", "3600"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: notes-data
```

```bash
lab_kubectl apply -f volume-lab.yaml
lab_kubectl -n service-lab wait --for=condition=Ready pod/volume-check --timeout=120s
lab_kubectl -n service-lab get pvc notes-data
lab_kubectl -n service-lab exec volume-check -- sh -c 'echo persisted > /data/message'
lab_kubectl -n service-lab delete pod volume-check
lab_kubectl apply -f volume-lab.yaml
lab_kubectl -n service-lab wait --for=condition=Ready pod/volume-check --timeout=120s
lab_kubectl -n service-lab exec volume-check -- cat /data/message
```

PVC가 `Bound`이고 마지막 출력이 `persisted`인지 확인한다. 실습 데이터를 없애도 되는 경우에는 Pod를 먼저 삭제하고 반환 정책을 확인한 뒤 `notes-data` PVC를 삭제한다. [Kubernetes · PV 반환 정책](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming)
