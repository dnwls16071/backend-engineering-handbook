# Amazon EKS Autoscaling, GitOps, and Observability

## 1. Pod와 노드 확장의 조건

| 동작 | 판단 기준 | 변경 대상 |
| --- | --- | --- |
| Horizontal Pod Autoscaler | 설정한 지표와 목표치. CPU 사용률이면 Pod의 CPU 요청량이 계산에 쓰인다. | Deployment 등의 레플리카 수 |
| Cluster Autoscaler | 기존 노드에 배치할 수 없는 Pod를 새 노드로 수용할 수 있는지 평가한다. | 관리하는 노드 그룹의 용량 |

HPA가 Pod를 늘려도 배치할 자원이 없으면 Pod가 `Pending`으로 남을 수 있다. EKS에서 Cluster Autoscaler를 사용할 때는 클러스터 버전과 호환되는 릴리스, 관리하는 노드 그룹과 탐색 태그, 해당 그룹에 한정된 IAM 권한을 확인한다. 배치 실패의 원인이 자원 부족인지도 먼저 본다. 노드 셀렉터, taint, 스토리지 제약도 Pod를 배치하지 못하게 할 수 있다. [Kubernetes · Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [Amazon EKS · Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)

부하 테스트에서는 `kubectl get hpa -n catalog`, Pod 이벤트, 노드 그룹의 용량을 시간순으로 비교한다. HPA에 CPU 지표가 표시되지 않으면 메트릭 수집 경로와 리소스 요청량을 확인한다. 노드 용량이 늘어도 RDS 커넥션이나 외부 서비스의 처리 한계는 별도로 관리한다. [Kubernetes · HPA Walkthrough](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)

## 2. Argo CD에서 Git 상태를 배포 상태로 연결하기

Argo CD `Application`에는 Git 저장소, 매니페스트 경로, 대상 클러스터와 Namespace를 지정한다. 대시보드에서 현재 리비전과 `Synced`, `Healthy`를 구분해 본다. 동기화 상태는 Git과 클러스터 리소스의 일치 여부이고, 건강 상태는 각 리소스의 설정된 평가 기준에 따른다. 실제 API 호출은 별도로 확인한다. [Argo CD · Getting Started](https://argo-cd.readthedocs.io/en/stable/getting_started/) · [Argo CD · Resource Health](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/)

자동 동기화, 자동 삭제(prune), 드리프트 보정(self-heal)은 정책에 따라 선택한다. GitOps 환경에서 롤백하려면 검증한 이전 배포 설정을 Git에서 복원해 선언 상태와 실제 상태를 일치시킨다. HPA가 관리하는 레플리카 수를 Git 설정에서도 계속 고정하면 두 제어 루프가 같은 필드를 바꿀 수 있으므로 소유권을 정한다. [Argo CD · Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) · [Kubernetes · HPA와 Deployment](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

## 3. Prometheus와 Grafana로 배포 결과 읽기

Prometheus는 설정한 타깃에서 메트릭을 수집해 시계열로 저장한다. Grafana 패널에서 요청량, 오류율, 지연 시간과 Pod 준비 상태를 같은 시간 범위로 볼 수 있다. Spring Boot에서는 Prometheus 레지스트리와 Actuator 엔드포인트 설정을 맞춘다. 메트릭의 상세 경로와 실제 지표 이름은 애플리케이션 구성을 확인한다. [Prometheus · Overview](https://prometheus.io/docs/introduction/overview/) · [Grafana · Dashboards](https://grafana.com/docs/grafana/latest/visualizations/dashboards/) · [Spring Boot 3.5 · Actuator Endpoints](https://docs.spring.io/spring-boot/3.5/reference/actuator/endpoints.html)

배포 직후 오류율이 상승하면 배포 리비전, Pod 재시작과 readiness, ALB 타깃 건강 상태를 함께 비교한다. Grafana 조회와 Kubernetes HPA에는 서로 다른 메트릭 전달 경로가 쓰일 수 있다. [Kubernetes · HPA 지표 API](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
