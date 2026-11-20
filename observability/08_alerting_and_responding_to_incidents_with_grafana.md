# Alerting and Responding to Incidents with Grafana

## 1. Prometheus 규칙으로 지연과 오류 감지하기

Prometheus는 `PrometheusRule`의 PromQL을 평가하고, Alertmanager는 발화한 알림을 묶어 설정된 수신자로 전달한다. Grafana에서는 대시보드와 세 가지 Drilldown으로 영향을 받은 요청을 조사한다. 이 실습 규칙은 `sns-api`의 `/lab/observability`에 한정한다. [메트릭 수집과 대시보드](05_monitoring_spring_boot_with_prometheus_and_grafana.md), [Prometheus 알림 규칙](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/), [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)

`k8s/sns-lab-rules.yaml`로 저장한다. 최근 2분에 p95가 500밀리초를 넘거나 5xx 오류율이 20%를 넘으면 각각의 알림 후보가 된다. 두 규칙 모두 초당 평균 요청이 0.25건을 넘어야 하므로 요청이 드문 구간에서 소수의 표본으로 발화할 가능성을 줄인다. 예시의 임계치와 평가 시간은 로컬 실습용이다. [PrometheusRule API](https://prometheus-operator.dev/docs/api-reference/api/#monitoring.coreos.com/v1.PrometheusRule)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: sns-lab
  namespace: sns
  labels: {release: obs}
spec:
  groups:
    - name: sns-lab
      interval: 15s
      rules:
        - alert: SnsLabHighLatency
          expr: |
            histogram_quantile(
              0.95,
              sum by (namespace, service, le) (
                rate(http_server_requests_seconds_bucket{namespace="sns",service="sns-api",uri="/lab/observability"}[2m])
              )
            ) > 0.5
            and
            sum by (namespace, service) (
              rate(http_server_requests_seconds_count{namespace="sns",service="sns-api",uri="/lab/observability"}[2m])
            ) > 0.25
          for: 1m
          labels: {severity: warning}
          annotations:
            summary: "SNS 실습 경로의 p95가 500ms를 초과했습니다."
        - alert: SnsLabHighErrorRate
          expr: |
            (
              sum by (namespace, service) (
                rate(http_server_requests_seconds_count{namespace="sns",service="sns-api",uri="/lab/observability",status=~"5.."}[2m])
              )
              /
              sum by (namespace, service) (
                rate(http_server_requests_seconds_count{namespace="sns",service="sns-api",uri="/lab/observability"}[2m])
              )
            ) > 0.2
            and
            sum by (namespace, service) (
              rate(http_server_requests_seconds_count{namespace="sns",service="sns-api",uri="/lab/observability"}[2m])
            ) > 0.25
          for: 1m
          labels: {severity: warning}
          annotations:
            summary: "SNS 실습 경로의 5xx 오류율이 20%를 초과했습니다."
```

```bash
kubectl --context kind-sns apply -f k8s/sns-lab-rules.yaml
```

Prometheus의 `/rules`에서 두 규칙이 로드됐는지 확인한다. 조건이 참이면 `Pending`으로 전환되고, 1분 동안 평가마다 조건을 충족하면 `Firing`으로 넘어간다. 이후 조건이 해소되면 `Inactive`로 돌아간다. 수집이 끊겨도 식의 결과가 사라질 수 있으므로 복구는 정상 응답, 수집 상태, 메트릭을 함께 확인한다. [Prometheus 알림 상태](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

## 2. Alertmanager의 라우팅과 Slack 전달 확인하기

로컬 실습에서는 아래 포트 포워딩을 실행해 `http://127.0.0.1:9093`의 Alerts 화면에서 `Firing` 알림이 도착하는지 확인한다. 알림이 Prometheus에는 보이고 Alertmanager에 없다면 Prometheus의 Alertmanager 대상 연결을 확인한다. 두 화면에서 알림을 볼 수 있어도 수신자 설정과 그룹 대기 시간은 메시지 전달에 영향을 준다. [Alertmanager 설정](https://prometheus.io/docs/alerting/latest/configuration/)

```bash
kubectl --context kind-sns -n monitoring port-forward svc/obs-alertmanager 9093:9093
```

Slack을 연결할 때의 `AlertmanagerConfig` 예시다. 앞 편의 차트 설정에서 Alertmanager는 여러 Namespace의 이 리소스를 읽으며, 기본 Namespace 매칭에 따라 아래 라우트는 `namespace="sns"`인 알림에 적용된다. `apiURL`은 같은 Namespace에 있는 Secret의 키를 참조한다. Slack은 Incoming Webhook을 발급할 때 지정한 채널로 메시지를 보내므로 채널은 웹훅 발급 시 선택한다. 로컬 실습은 Alertmanager 화면만으로 진행할 수 있다. [Alertmanager 차트 설정](https://github.com/prometheus-community/helm-charts/blob/kube-prometheus-stack-92.10.0/charts/kube-prometheus-stack/values.yaml), [AlertmanagerConfig API](https://prometheus-operator.dev/docs/api-reference/api/#monitoring.coreos.com/v1alpha1.AlertmanagerConfig), [Slack Incoming Webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: sns-lab-slack
  namespace: sns
spec:
  route:
    receiver: sns-lab-slack
    matchers:
      - name: alertname
        matchType: "=~"
        value: "SnsLab(HighLatency|HighErrorRate)"
    groupBy: [alertname, namespace, service]
    groupWait: 15s
    groupInterval: 1m
    repeatInterval: 1h
  receivers:
    - name: sns-lab-slack
      slackConfigs:
        - apiURL:
            name: sns-lab-slack
            key: webhook-url
          channel: "#sns-lab-alerts"
          sendResolved: true
```

`groupBy`의 라벨이 같은 알림은 한 그룹으로 묶인다. `groupWait`는 그룹의 첫 알림을 보내기 전 대기 시간이고, `groupInterval`은 이미 전달한 그룹에 변동이 있는지 확인하는 간격이다. `sendResolved`를 설정하면 앞서 전달한 알림이 해소됐을 때 수신자에 해소 알림을 보낼 수 있다. [Alertmanager 라우팅과 Slack 설정](https://prometheus.io/docs/alerting/latest/configuration/#route)

## 3. 로컬 kind에서 정상·지연·오류 재현하기

Spring MVC 앱의 컴포넌트 스캔 범위에 아래 컨트롤러를 추가한다. 테스트 이미지를 빌드해 로컬 kind에 로드하고 `sns-api` Deployment에 새 이미지 태그를 지정한다. 컨테이너의 `SPRING_PROFILES_INCLUDE`에 `observability-lab`을 추가한다. 앞 편의 Gateway는 `/api`를 연결하므로 이 실습 경로에는 Service 포트 포워딩으로 접근한다. [kind 앱 배포](02_deploying_spring_boot_on_kind_with_gateway_api.md), [Spring Boot 3.5 Profiles](https://docs.spring.io/spring-boot/3.5/reference/features/profiles.html)

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Profile("observability-lab")
@RestController
class ObservabilityLabController {
    private static final Logger log =
        LoggerFactory.getLogger(ObservabilityLabController.class);

    @GetMapping("/lab/observability")
    ResponseEntity<String> observe(
        @RequestParam(name = "mode", defaultValue = "normal") String mode
    ) throws InterruptedException {
        return switch (mode) {
            case "normal" -> ResponseEntity.ok("ok");
            case "latency" -> {
                Thread.sleep(800);
                log.warn("SNS observability lab: injected latency");
                yield ResponseEntity.ok("delayed");
            }
            case "error" -> {
                log.error("SNS observability lab: injected error");
                yield ResponseEntity.internalServerError().body("injected error");
            }
            default -> ResponseEntity.badRequest().body("unknown mode");
        };
    }
}
```

`kubectl --context kind-sns -n sns port-forward svc/sns-api 8080:8080`을 연 뒤 아래 함수를 사용한다. `normal`로 기준선을 만든 다음 `latency`를 실행해 HTTP 200과 약 800밀리초 지연을 확인한다. `normal`을 다시 실행해 지연 알림이 해소되면 `error`로 HTTP 500과 오류율 상승을 확인한다. 한 단계씩 실행하며 시작 시각을 기록한다.

```bash
run_sns_lab() {
  local mode="$1"
  for attempt in $(seq 1 180); do
    curl -sS --max-time 3 -o /dev/null -w '%{http_code} %{time_total}s\n' \
      "http://127.0.0.1:8080/lab/observability?mode=${mode}" || return
    sleep 1
  done
}

run_sns_lab normal
run_sns_lab latency
run_sns_lab normal
run_sns_lab error
run_sns_lab normal
```

## 4. Grafana Drilldown으로 확인하고 복구 판단하기

Grafana의 시간 범위를 기록한 장애 시각으로 맞춘다. 앞 편의 Loki·Tempo 데이터 소스를 사용하고, Logs Drilldown이 서비스별 로그 볼륨을 읽을 수 있도록 Loki의 Volume API를 활성화한다. [Loki 로그 수집](06_centralizing_spring_boot_logs_with_opentelemetry_and_loki.md), [Logs Drilldown 설정](https://grafana.com/docs/grafana/latest/visualizations/simplified-exploration/logs/access/)

Traces Drilldown에는 TraceQL 메트릭이 필요하다. Tempo 3.0의 단일 바이너리 모드에서는 live-store가 최근 트레이스의 메트릭 조회를 처리한다. Grafana Explore에서 Tempo를 선택하고 `{ resource.service.name = "sns-api" } | rate()`로 먼저 확인한다. [Tempo 트레이스 수집](07_tracing_distributed_requests_with_opentelemetry_and_tempo.md), [Tempo live-store](https://grafana.com/docs/tempo/latest/reference-tempo-architecture/components/live-store/), [Traces Drilldown 요구 사항](https://grafana.com/docs/plugins/grafana-exploretraces-app/latest/access/)

| 화면 | 확인할 내용 |
| :--- | :--- |
| Drilldown → Metrics | Prometheus에서 `namespace=sns`, `service=sns-api`, `uri=/lab/observability`로 범위를 좁힌다. 요청 수와 지연을 보고, 필요하면 Explore에 앞 편의 PromQL을 붙여 `uri="/lab/observability"`와 `[2m]`로 변경하면 알림 계산과 같은 범위를 볼 수 있다. |
| Drilldown → Logs | Loki에서 `service_name=sns-api`와 해당 시각을 선택한다. `injected latency` 또는 `injected error`를 찾아 어떤 모드가 실행됐는지 확인한다. 로그에 trace ID가 있으면 동일한 요청의 트레이스를 열 수 있다. |
| Drilldown → Traces | Tempo에서 `resource.service.name=sns-api`로 필터링한다. 지연 구간에서는 긴 서버 span을, 오류 구간에서는 실패한 span과 HTTP 상태를 본다. |

마지막 `normal` 구간에서 HTTP 200, 정상 요청률, p95 하락, 5xx 오류율 하락을 확인한다. `[2m]`에 장애 샘플이 남아 있는 동안 메트릭과 알림은 늦게 회복될 수 있다. 스크레이프가 계속 성공하는 상태에서 알림이 `Inactive`로 돌아오면 장애 시작·발화·복구 시각과 조사에 사용한 trace ID를 기록한다. 실습이 끝나면 `observability-lab` 프로필을 빼고 다시 배포한다. [Grafana Drilldown](https://grafana.com/docs/grafana/latest/visualizations/simplified-exploration/), [PromQL의 `rate()`](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate)
