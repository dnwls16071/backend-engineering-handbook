# 쿠버네티스 로깅에서 OpenTelemetry 수집과 Loki 저장·조회 이해하기

## 1. 컨테이너 로그를 노드에서 수집해 중앙에 보관한다

- **앱이 `stdout`·`stderr`로 출력하면 컨테이너 런타임이 노드에 로그 파일을 기록한다.** 일반적인 Linux 노드에서 기본 경로는 `/var/log/pods`이며 kubelet이 로그 회전을 관리한다. Pod 교체나 노드 장애 뒤에도 로그를 조회하려면 외부 백엔드에 전송해 보관한다. [Kubernetes 로깅 아키텍처](https://kubernetes.io/docs/concepts/cluster-administration/logging/), [Pod 종료 상태와 이전 로그](09_pod.md)
- 노드 로그를 읽는 수집기는 보통 DaemonSet으로 배치한다. 앱에서 OpenTelemetry SDK로 계측하는 경우에는 로그를 OTLP로 Collector에 보낼 수도 있다. 같은 로그를 표준 출력과 OTLP 양쪽으로 수집하면 중복 저장될 수 있다. [DaemonSet과 노드별 수집](13_kubernetes_patterns.md), [OpenTelemetry Collector 배포 형태](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/)

| 계층 | 강의에 나온 도구 | 역할 |
| :--- | :--- | :--- |
| 수집·전송 | Logstash, Fluent Bit, Promtail, Grafana Alloy, OpenTelemetry Collector | 노드 로그나 앱이 보낸 데이터를 받아 파싱·변환하고 백엔드에 전달한다. |
| 저장·검색 | Elasticsearch, OpenSearch, Loki | 로그를 보관하고 쿼리를 처리한다. Loki는 스트림 라벨과 시간으로 검색 범위를 좁힌다. |
| 조회 화면 | Kibana, OpenSearch Dashboards, Grafana | 백엔드를 조회해 로그를 탐색하고 다른 관측 지표와 함께 표시한다. |

- OpenSearch와 OpenSearch Dashboards는 Elasticsearch와 Kibana의 마지막 Apache 2.0 버전인 7.10.2에서 파생되었다. Promtail은 2026년 3월 2일 지원이 종료되었다. Grafana Alloy는 OpenTelemetry Collector 구성요소와 Prometheus 수집 기능을 포함하는 배포판이다. [OpenSearch FAQ](https://opensearch.org/faq/), [Promtail 지원 종료](https://grafana.com/docs/loki/latest/send-data/promtail/), [Grafana Alloy 개요](https://grafana.com/docs/opentelemetry/collector/)

## 2. Loki 배포 방식은 읽기·쓰기를 얼마나 독립적으로 확장할지에 따라 달라진다

| 배포 방식 | 구성 | 운영에서 달라지는 점 |
| :--- | :--- | :--- |
| Monolithic | 읽기·쓰기·저장 관리 컴포넌트를 한 프로세스에서 실행한다. | 소규모에 구성이 단순하다. 고가용성이 필요하면 공유 객체 저장소와 복제 설정을 함께 검토한다. |
| Simple Scalable(SSD) | 컴포넌트를 `read`, `write`, `backend` 세 그룹으로 나눈다. | 강의의 아키텍처가 사용하는 방식이다. Loki 4.0부터 이 배포 모드를 사용할 수 없다. |
| Distributed·Microservices | Distributor, Ingester, Querier 등 컴포넌트를 개별 배포한다. | 읽기와 쓰기 병목에 맞춰 각각 확장할 수 있으며 배포·운영할 대상이 많아진다. |

- 일일 로그 유입량과 함께 피크 쓰기량, 동시 쿼리 수, 보존 기간, 고가용성 요구를 본다. Loki 인스턴스마다 독립 파일 저장소를 두고 Service로 분산하면 조회 대상에 따라 결과가 달라질 수 있다. 여러 인스턴스가 같은 로그를 조회해야 한다면 공유 저장소와 복제 구성을 함께 설계한다. [Loki 배포 모드](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- Loki Gateway를 두면 Collector의 쓰기 요청과 Grafana의 읽기 요청을 각각 담당 컴포넌트로 전달할 수 있다. 외부에 Loki API를 노출하는 환경에서는 프록시에서 인증과 테넌트 헤더를 관리한다. [Loki Gateway 구조](https://grafana.com/docs/loki/latest/get-started/quick-start/quick-start/), [Loki 인증 문서](https://grafana.com/docs/loki/latest/operations/authentication/)

## 3. 라벨과 시간으로 인덱스를 찾고 청크에서 로그를 읽는다

- **Loki의 스트림은 같은 라벨 집합을 가진 로그 항목의 묶음이다.** 인덱스는 스트림·시간과 해당 청크를 연결한다. 청크에는 로그 본문과 타임스탬프, 설정에 따라 구조화 메타데이터가 들어간다. TSDB는 Loki의 인덱스 방식이다. 객체 저장소를 쓰는 Single Store 구성에서는 인덱스 파일과 청크 파일이 같은 객체 저장소에 보관된다. [Loki 아키텍처](https://grafana.com/docs/loki/latest/get-started/architecture/), [Loki TSDB 인덱스](https://grafana.com/docs/loki/latest/operations/storage/tsdb/)

| 경로 | 구성요소 | 처리 흐름 |
| :--- | :--- | :--- |
| 쓰기 | Distributor → Ingester | Distributor가 스트림을 담당 Ingester와 복제본에 전달한다. Ingester는 로그를 청크로 묶어 스토리지에 기록한다. |
| 읽기 | Query Frontend → Query Scheduler → Querier | Query Frontend가 요청을 나누고 Scheduler가 작업을 대기열로 관리한다. Querier가 Ingester의 최신 데이터와 저장된 청크를 조회한다. |
| 인덱스·보존 | Index Gateway, Compactor | Index Gateway는 조회에 필요한 인덱스 접근을 제공한다. Compactor는 인덱스를 정리하고 설정된 보존 정책을 적용한다. |

- S3 호환 객체 저장소는 로그와 인덱스를 보존하는 계층이다. Ingester의 WAL처럼 컴포넌트가 재시작 후 복구에 사용하는 로컬 상태는 별도로 고려한다. [Loki WAL](https://grafana.com/docs/loki/latest/operations/storage/wal/), [Loki 로그 보존](https://grafana.com/docs/loki/latest/operations/storage/retention/), [쿠버네티스 스토리지와 PV·PVC](12_pv_and_pvc.md)

## 4. OpenTelemetry Collector는 수신·처리·전송을 파이프라인으로 연결한다

| 구성요소 | 역할 | 로그 수집에서의 예 |
| :--- | :--- | :--- |
| Receiver | 파일이나 네트워크로 데이터를 받는다. | `filelog`는 노드의 컨테이너 로그를 읽고, `otlp`는 SDK나 다른 Collector에서 데이터를 받는다. |
| Processor | 받은 데이터에 속성을 추가하거나 변환하고 전송량을 관리한다. | `k8sattributes`로 Pod·Namespace 정보를 추가하고 `transform`으로 본문이나 속성을 가공한다. `memory_limiter`와 `batch`는 각각 메모리 사용 관리와 전송 묶음에 쓰인다. |
| Exporter | 처리한 신호를 목적지에 전달한다. | Loki의 네이티브 OTLP 수집에는 OTLP/HTTP를 사용한다. 메트릭과 트레이스는 해당 백엔드에 전달할 수 있다. |
| Connector | 한 파이프라인의 출력과 다른 파이프라인의 입력을 연결한다. | 지원되는 Connector를 사용해 로그 건수나 오류 건수를 메트릭으로 내보낸다. |
| Extension | 파이프라인 외부에서 진단 등 보조 기능을 제공한다. | 상태 점검과 `zpages` 진단에 사용한다. |

- `service.pipelines`에서 `logs`, `metrics`, `traces`에 사용할 Receiver·Processor·Exporter를 연결한다. Extension은 `service.extensions`에서 활성화한다. Collector 이미지에 필요한 컴포넌트가 포함되어 있는지도 확인한다. [OpenTelemetry Collector 구성](https://opentelemetry.io/docs/collector/configuration/), [Loki의 OTLP 로그 수집](https://grafana.com/docs/loki/latest/send-data/otel/)
- 노드 파일 수집은 DaemonSet, 여러 앱의 OTLP 수신은 중앙 Deployment로 구성할 수 있다. Kubernetes 이벤트처럼 클러스터 범위에서 읽는 데이터는 단일 활성 수집기 등으로 중복 수집을 막는다. Pod 속성 보강이나 이벤트 조회에는 필요한 Kubernetes API 권한을 별도로 연결한다. [OpenTelemetry Collector Helm 차트](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/), [ServiceAccount와 RBAC](09_pod.md)

## 5. 앱은 메시지와 검색에 필요한 필드를 구조화해 기록한다

| OpenTelemetry 로그 모델 | 담는 정보 | 활용 |
| :--- | :--- | :--- |
| Resource | 신호를 생성한 서비스·배포 환경·Kubernetes 리소스 | 여러 로그 항목에 공통인 서비스와 실행 환경을 식별한다. |
| Instrumentation Scope | 로그를 생성한 계측 라이브러리나 모듈의 범위 | 같은 서비스 안에서 어느 계측 코드가 기록했는지 구분한다. |
| LogRecord | 시각, 심각도, `Body`, Attributes, `TraceId`·`SpanId` 등 | 개별 사건의 메시지와 세부 조건을 담고 관련 트레이스와 연결한다. |

- 앱이 JSON 로그를 표준 출력에 기록하면 Collector가 필요한 필드를 파싱해 LogRecord 속성으로 옮길 수 있다. SDK가 이미 구조화한 로그를 보내는 경우에는 해당 필드를 활용한다. 본문과 속성의 이름을 서비스 간 일관되게 유지하면 로그 조회와 트레이스 연계가 쉬워진다. [OpenTelemetry 로그 데이터 모델](https://opentelemetry.io/docs/specs/otel/logs/data-model/), [OpenTelemetry 로그 개념](https://opentelemetry.io/docs/concepts/signals/logs/)
- `trace_id`는 동일 요청의 로그를 연결할 때 유용하다. 사용자 식별자는 필요한 경우에만 정책에 맞춰 저장한다. 토큰·비밀번호 등은 앱에서 출력하지 않고, 민감한 필드가 들어올 수 있는 경로는 Collector에서 제거하거나 마스킹한다. [OpenTelemetry 민감 데이터 처리](https://opentelemetry.io/docs/security/handling-sensitive-data/)

## 6. 자주 쓰는 분류는 인덱스 라벨에, 개별 식별자는 구조화 메타데이터에 둔다

| Loki의 저장 위치 | 담을 정보 | 조회할 때의 쓰임 |
| :--- | :--- | :--- |
| 인덱스 라벨 | `service_name`, `k8s_namespace_name`, 환경처럼 비교적 안정적인 분류 값 | 라벨과 시간으로 읽을 스트림을 좁힌다. |
| 구조화 메타데이터 | `trace_id`, Pod 식별자처럼 값 종류가 많고 개별 로그를 찾는 데 필요한 속성 | 선택한 스트림 안에서 속성으로 필터링할 수 있다. |
| 로그 본문 | 오류 메시지, 업무 이벤트, 진단에 필요한 세부 내용 | 문자열로 필터링하거나 JSON이면 필요한 필드를 파싱한다. |

- **값 종류가 많은 필드를 인덱싱하면 라벨 조합이 늘어나고 스트림이 잘게 나뉜다.** `k8s.pod.name`과 `service.instance.id`가 OTLP 기본 매핑에 포함되어 있더라도 카디널리티가 높을 수 있으므로 필요한 경우 구조화 메타데이터로 옮긴다. [Loki OTLP 속성 매핑](https://grafana.com/docs/loki/latest/send-data/otel/), [Loki 구조화 메타데이터](https://grafana.com/docs/loki/latest/get-started/labels/structured-metadata/)
- Loki는 OTLP의 Resource 속성 가운데 지정한 일부를 인덱스 라벨로 올리고, 나머지 속성은 매핑 설정에 따라 구조화 메타데이터에 저장하거나 버린다. LogRecord의 `Body`는 로그 본문이 된다. 속성 키의 점은 밑줄로 정규화되므로 `service.name`은 Loki에서 `service_name`으로 조회한다. 네이티브 OTLP 수집에는 구조화 메타데이터를 지원하는 TSDB 인덱스와 스키마 `v13` 이상이 필요하다. [Loki OTLP 속성 매핑](https://grafana.com/docs/loki/latest/send-data/otel/), [Loki 구조화 메타데이터](https://grafana.com/docs/loki/latest/get-started/labels/structured-metadata/)

## 7. LogQL은 스트림을 먼저 좁힌 뒤 필요한 로그를 찾는다

- Grafana에서 Loki를 조회할 때는 시간 범위와 서비스·Namespace 같은 인덱스 라벨로 후보 스트림을 좁힌다. 그 안에서 구조화 메타데이터나 본문으로 필터링하고, 본문에만 있는 JSON 필드는 파싱해서 조건을 적용한다. [LogQL 로그 쿼리](https://grafana.com/docs/loki/latest/query/log_queries/)
- 장애 분석에서는 Prometheus와 Grafana에서 오류율이 오른 시간과 서비스를 찾고, 같은 범위의 Loki 로그에서 실패 이유와 `trace_id`를 확인할 수 있다. 트레이스 백엔드까지 연계했다면 같은 ID로 서비스 간 호출 흐름을 따라간다. [쿠버네티스 모니터링과 Grafana](15_kubernetes_monitoring.md), [OpenTelemetry 로그 데이터 모델](https://opentelemetry.io/docs/specs/otel/logs/data-model/)

## 8. 로그가 없거나 중복되면 수집과 조회 경로를 순서대로 확인한다

| 증상 | 먼저 확인할 내용 |
| :--- | :--- |
| 특정 노드의 로그만 없다. | 수집기가 해당 노드에 배치됐는지, 로그 경로와 파일 읽기 권한이 맞는지 확인한다. |
| Collector에서 읽었지만 Loki에 없다. | 로그 파이프라인 연결, OTLP/HTTP 목적지, 인증·테넌트와 전송 오류를 확인한다. |
| Loki에 로그가 있지만 Grafana에서 찾을 수 없다. | 데이터 소스와 테넌트, 조회 시간, 인덱스 라벨인지 구조화 메타데이터인지 확인한다. |
| 같은 로그가 여러 번 표시된다. | 같은 노드 파일을 읽는 수집기나 stdout·SDK 전송이 겹치는지 확인한다. 클러스터 이벤트 수집기가 여러 복제본에서 같은 대상을 감시하는지도 본다. |
| 전송 장애 뒤 로그가 비어 있다. | 로그 회전과 읽기 위치 기록, Exporter의 큐 크기·재시도 한도, 필요 시 큐의 영속 저장을 확인한다. |

- 수집기와 Loki 사이 장애는 앱 로그가 정상 출력되는 상황에서도 발생할 수 있다. Collector의 전송 실패·드롭·큐 상태와 Loki의 수집 오류를 관측하면 로그 유실 지점을 좁힐 수 있다. [OpenTelemetry Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/)
