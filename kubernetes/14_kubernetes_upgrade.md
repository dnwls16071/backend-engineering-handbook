# 쿠버네티스 업그레이드 전략과 노드 스케줄링 이해하기

## 1. 릴리스 지원 기간과 컴포넌트 버전 차이를 확인한다

- Kubernetes 버전은 `Major.Minor.Patch` 형식이다. 업스트림은 대략 4개월마다 Minor 버전을 출시하고 최근 세 Minor 릴리스 브랜치를 관리한다. 일반 패치 지원은 약 1년이며, 이후 유지보수 기간에는 심각한 문제에 한해 패치가 추가될 수 있다. 목표 버전의 지원 종료일은 릴리스 목록에서 확인한다. [Kubernetes 릴리스 목록](https://kubernetes.io/releases/), [릴리스 주기](https://kubernetes.io/releases/release/), [패치 릴리스 정책](https://kubernetes.io/releases/patch-releases/)
- **kubeadm 기반 클러스터의 Minor 업그레이드는 한 단계씩 진행한다.** 같은 Minor 안에서는 중간 Patch를 모두 설치할 필요가 없다. Minor를 올릴 때는 출발·도착 버전의 최신 Patch와 릴리스 노트를 검토한다. [kubeadm 업그레이드 문서](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/), [Kubernetes Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)

| 컴포넌트 | 계획에 영향을 주는 버전 관계 |
| :--- | :--- |
| `kube-apiserver` | HA 구성에서 가장 오래된 인스턴스와 가장 새 인스턴스의 차이는 최대 한 Minor이다. |
| `kubelet` | 연결되는 API 서버보다 새 버전을 사용할 수 없다. 업스트림은 `1.25` 이상 kubelet에 대해 최대 세 Minor 이전까지 허용한다. |
| `kube-proxy` | API 서버와의 버전 차이, `kube-proxy`가 실행되는 노드의 kubelet과의 버전 차이를 각각 확인한다. |
| `kubectl` | API 서버 기준 한 Minor 이전부터 한 Minor 이후까지 지원한다. HA 구성에서는 모든 API 서버에 대해 이 범위를 만족해야 한다. |

- 컴포넌트별 버전 차이 허용 범위는 순차 작업 중 혼재하는 버전을 판단하는 기준이다. 클러스터 배포 도구나 관리형 서비스는 추가 제약을 둘 수 있다. [Kubernetes Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)

## 2. 기존 클러스터 업그레이드와 새 클러스터 전환을 비교한다

| 전략 | 유지하거나 다시 준비할 것 | 운영과 복구에서 확인할 점 |
| :--- | :--- | :--- |
| 기존 클러스터에서 순차 업그레이드 | 기존 워크로드 선언, 외부 인프라와 스토리지 연결을 유지할 수 있다. | Minor 단계와 노드 수만큼 작업이 늘어난다. 문제가 발생하면 해당 단계의 복구 절차와 사전 백업을 사용한다. |
| 새 클러스터를 병행 구축한 뒤 트래픽 전환 | 새 클러스터에 애드온·앱·네트워크·권한을 다시 구성하고 필요한 데이터를 이관한다. | 두 환경을 유지할 자원이 필요하다. 기존 클러스터로 트래픽을 되돌릴 수 있는 기간과 쓰기 데이터의 복구 방법을 정한다. |
| 기존 클러스터를 제거한 뒤 재구축 | 새 클러스터에 앱과 설정을 재배포하고 저장 데이터의 복원을 준비한다. | 두 환경을 함께 유지할 필요는 없으며, 재구축과 서비스 복구 사이에 중단 시간이 생긴다. |

- **기존 환경을 유지하는 방법은 노드별 작업 시간과 가용 용량이 중요하고, 새 환경으로 전환하는 방법은 데이터 이관과 되돌리기 조건이 중요하다.** 예를 들어 새 클러스터가 쓰기를 받은 뒤 요청만 기존 클러스터로 돌리면 두 환경의 데이터가 달라질 수 있다. 쓰기 중단, 공유 저장소 또는 복제 등 데이터 전환 방식을 먼저 정한다. [트래픽 전환](07_jenkins_pipeline_from_basics_to_blue_green.md), [PV·PVC와 볼륨 연결](12_pv_and_pvc.md)
- kubeadm 업그레이드 실패 시 단계에 따라 컴포넌트 자동 복구나 백업 복원이 가능하다. 기존 클러스터의 버전 다운그레이드를 복구 절차로 가정하지 않는다. 병행 구축에서는 기존 클러스터를 보존한 상태에서 트래픽을 되돌릴 수 있다. [kubeadm 실패 복구 문서](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/#recovering-from-a-failure-state)

## 3. 대체 Pod가 배치될 노드를 스케줄링 조건으로 판단한다

| 설정 | 선택 기준 | 노드 작업에 미치는 영향 |
| :--- | :--- | :--- |
| `nodeSelector` | 후보 노드에 지정한 라벨이 모두 있어야 한다. | 같은 라벨을 가진 다른 노드가 있어야 대체 Pod를 배치할 수 있다. |
| `nodeAffinity` | 노드 라벨에 필수 조건과 선호 조건을 표현한다. | 필수 조건은 후보를 제한하고 선호 조건은 후보 점수에 영향을 준다. |
| `nodeName` | 이름으로 노드를 직접 지정해 스케줄러를 우회한다. | 지정 노드를 교체하거나 사용할 수 없을 때 자동으로 다른 노드를 찾기 어렵다. |
| `podAffinity` | 특정 라벨의 Pod가 있는 토폴로지 영역에 함께 배치한다. | 함께 있어야 할 Pod가 어느 노드나 영역에 남는지 확인한다. |
| `podAntiAffinity` | 특정 라벨의 Pod가 있는 토폴로지 영역을 피한다. | 다른 영역이 부족하면 필수 분산 조건을 만족하지 못해 대체 Pod가 `Pending`일 수 있다. |

- `requiredDuringSchedulingIgnoredDuringExecution`은 배치 시 충족해야 하는 조건이다. `preferredDuringSchedulingIgnoredDuringExecution`은 충족하는 후보에 가중치를 준다. 배치 이후 라벨이 바뀌어도 이 조건만으로 이미 실행 중인 Pod가 퇴거되지는 않는다.
- Pod affinity와 anti-affinity에서 `topologyKey`는 같은 범위를 결정하는 노드 라벨 키이다. `kubernetes.io/hostname`은 노드 단위, `topology.kubernetes.io/zone`은 가용 영역 단위의 배치에 사용한다. 실제 요청을 어디로 보낼지는 Service의 엔드포인트와 트래픽 정책이 결정한다. [Kubernetes Pod 배치 문서](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/), [Service 트래픽 정책](10_service.md)
- **남은 노드의 전체 용량과 특정 Pod가 실제로 쓸 수 있는 용량을 함께 확인한다.** CPU·메모리가 충분해도 노드 라벨, taint, 분산 조건 또는 PV의 노드·영역 제약 때문에 배치가 막힐 수 있다. [PV·PVC와 노드 배치](12_pv_and_pvc.md)

## 4. Taint와 Toleration으로 배치 제한과 예외를 정한다

| Taint 효과 | 새 Pod에 미치는 영향 | 실행 중인 Pod에 미치는 영향 |
| :--- | :--- | :--- |
| `NoSchedule` | 매칭되는 toleration이 없는 Pod는 스케줄러가 해당 노드에 배치하지 않는다. | 기존 Pod는 계속 실행된다. |
| `PreferNoSchedule` | 스케줄러가 해당 노드를 피하려고 한다. | 기존 Pod는 계속 실행된다. |
| `NoExecute` | 매칭되는 toleration이 없는 Pod는 해당 노드에 배치할 수 없다. | 매칭이 없으면 퇴거 대상이 되고, `tolerationSeconds`가 있으면 그 기간 동안 남을 수 있다. |

- Toleration은 매칭되는 taint의 제약을 통과하게 한다. 특정 전용 노드를 사용하게 하려면 `nodeSelector`나 `nodeAffinity`로 그 노드를 선택한다. 노드에 여러 taint가 있으면 앱이 통과해야 할 각 제약을 확인한다. `Exists`는 값 비교를 생략하고 `Equal`은 값을 비교한다.
- Kubernetes는 `not-ready`나 `unreachable` 상태에서 `NoExecute` taint를 적용할 수 있다. 별도 설정이 없는 일반 Pod에는 이 두 taint에 대한 300초 toleration이 기본으로 부여된다. DaemonSet Pod에는 시간 제한이 없는 해당 toleration이 들어간다. [Kubernetes Taints and Tolerations 문서](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)

## 5. 노드를 비우는 작업과 대체 Pod가 준비되는 시점을 구분한다

| 노드 작업 | 동작 |
| :--- | :--- |
| `cordon` | 노드를 스케줄링 불가 상태로 표시한다. 기존 Pod는 그 노드에서 계속 실행된다. |
| `drain` | 노드를 스케줄링 불가로 표시하고 대상 Pod의 퇴거와 종료를 기다린다. 컨트롤러가 관리하는 워크로드는 필요하면 대체 Pod를 만든다. |
| `uncordon` | 스케줄러가 다시 해당 노드를 새 Pod의 후보로 고려할 수 있게 한다. |

- **drain은 기존 Pod를 퇴거시키는 작업이다. 대체 Pod의 배치와 서비스 준비는 그 다음에 확인한다.** 컨트롤러가 없는 단독 Pod는 자동으로 재생성되지 않으며 DaemonSet Pod와 미러 Pod는 일반적인 drain 대상에서 제외된다. [노드 drain 가이드](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/), [kubectl drain 문서](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_drain/)
- PodDisruptionBudget(PDB)은 Eviction API를 사용하는 자발적 중단에서 유지할 가용 복제본 수를 보호한다. 예를 들어 복제본이 하나이고 `minAvailable: 1`이면 그 Pod의 퇴거가 막힐 수 있다. PDB 조건과 배치 여유를 확인하고, 필요하면 작업 전에 노드를 추가하거나 앱 복제본을 늘린다. [노드 drain 가이드](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- `emptyDir`의 데이터는 해당 Pod가 삭제되면 사라진다. `hostPath`나 local PV의 데이터는 노드에 의존하며, 스토리지 접근 모드와 영역 제약에 따라 대체 Pod의 볼륨 연결이 지연되거나 불가능할 수 있다. [PV·PVC와 볼륨 연결](12_pv_and_pvc.md)
- 사용자 요청을 처리하는 앱은 퇴거 중 요청 종료, 대체 Pod의 Ready 상태와 Service 엔드포인트 반영을 확인한다. 단일 복제본이나 저장소가 한 노드에 고정된 서비스의 유지보수 시간을 따로 고려한다. [Pod 종료 처리](09_pod.md), [Service와 EndpointSlice](10_service.md)

## 6. 배포 호환성과 복구 범위를 업그레이드 전에 검증한다

| 확인 대상 | 개발·검증 환경에서 확인할 내용 |
| :--- | :--- |
| 배포 파이프라인 | Helm·Kustomize 등으로 생성한 최종 매니페스트와 CI/CD가 목표 버전에서 동작하는지 확인한다. 제거된 `apiVersion`, CRD·Webhook과 RBAC에 의존하는 배포 단계도 확인한다. |
| 노드와 애드온 | OS·containerd, CNI, CSI, CoreDNS, metrics-server 등 실제 구성의 버전 호환성과 필요한 변경 순서를 확인한다. |
| etcd와 클러스터 설정 | etcd 스냅샷을 저장하고 복원이 가능한지 확인한다. 클러스터 설정과 복원에 필요한 인증 자료의 보존 범위도 확인한다. |
| 앱 데이터 | DB와 PV의 데이터는 별도 백업·복원 또는 이관 계획을 세운다. 새 클러스터에서 볼륨을 연결하고 앱이 데이터를 읽고 쓸 수 있는지 확인한다. |
| 서비스 가용성 | 노드를 비우는 동안 Ready 복제본과 요청 성공률을 관측하고, 카나리 요청으로 DNS·Ingress·DB 연결을 확인한다. |

- **etcd 스냅샷은 Kubernetes API의 클러스터 상태를 복원하는 데 쓰인다.** DB와 PV의 실제 데이터는 해당 백엔드의 복구 방식과 허용 가능한 데이터 손실 범위를 기준으로 보호한다. [Kubernetes etcd 운영 문서](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/), [PV·PVC와 볼륨 연결](12_pv_and_pvc.md)
- 제거된 API는 저장소의 YAML과 배포 도구가 렌더링한 결과에서 함께 확인한다. 예를 들어 직접 작성한 YAML을 수정했어도 Chart나 Operator가 이전 API를 생성할 수 있다. [Deprecated API Migration Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/), [Helm과 Kustomize](08_helm_vs_kustomize_comparing_and_using_together.md)

## 7. 컨트롤 플레인과 워커를 순차 작업하고 각 단계의 결과를 확인한다

| 단계 | 진행 기준 | 완료 확인 |
| :--- | :--- | :--- |
| 작업 전 | 버전 호환성, 백업·복원 가능 여부, PDB와 남은 노드 용량을 확인한다. | 주요 서비스의 기준 지표와 복구를 시작할 기준이 정해져 있다. |
| 컨트롤 플레인 | kubeadm 기반에서는 첫 컨트롤 플레인 노드부터 진행하고 추가 컨트롤 플레인 노드를 순차 처리한다. | API 서버가 응답하고 스케줄링·리소스 제어가 정상이다. HA 구성에서는 나머지 인스턴스와 etcd 가용성도 확인한다. |
| 워커 노드 | 워커를 한 대씩 또는 필요한 용량을 유지할 수 있는 소규모 단위로 작업한다. kubelet Minor를 올리기 전에 대상 노드를 drain한다. | kubelet 버전, 노드 `Ready`, 대체 Pod 준비와 서비스 요청이 정상이다. 유지보수 후 노드를 다시 배치 후보로 돌린다. |
| 단계 완료 | 각 Minor 단계와 애드온 변경 후 상태를 다시 확인한다. | DNS, 네트워크, 볼륨 연결, 배포 파이프라인과 주요 서비스의 오류율·지연이 허용 범위에 있다. |

- 컨트롤 플레인이 한 대라면 API 서버 재시작 중 배포·스케일링 등 API 작업이 잠시 영향을 받을 수 있다. 이미 실행 중인 서비스의 요청 처리 상태는 앱과 네트워크 구성에 따라 달라지므로 실제 트래픽으로 별도 확인한다. [kubeadm 업그레이드 문서](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)
