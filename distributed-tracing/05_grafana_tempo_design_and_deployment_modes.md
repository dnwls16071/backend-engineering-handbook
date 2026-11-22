# Grafana Tempo Design and Deployment Modes

Tempo는 Trace ID 조회와 TraceQL 검색을 제공하는 분산 추적 백엔드다. Tempo 2.10은 Span 데이터를 블록으로 묶고, 장기 보관용 백엔드에 저장한 블록도 조회 범위에 포함한다. [Tempo 2.10 아키텍처](https://grafana.com/docs/tempo/v2.10.x/introduction/architecture/) · [Tempo 2.10 HTTP API](https://grafana.com/docs/tempo/v2.10.x/api_docs/)

## 1. 블록과 객체 스토리지를 사용하는 이유

Ingester는 Span과 Resource 속성을 Parquet에 배치하고 여러 Trace의 데이터를 블록 단위로 내보낸다. 읽기 경로는 최근 데이터와 이미 저장된 블록을 조회할 수 있다. 실제 조회 비용은 시간 범위, 읽은 블록, 필터의 선택도에 따라 달라진다. [Tempo 2.10 아키텍처](https://grafana.com/docs/tempo/v2.10.x/introduction/architecture/) · [Tempo Parquet 블록](https://grafana.com/docs/tempo/v2.10.x/configuration/parquet/) · [Tempo 검색 성능](https://grafana.com/docs/tempo/v2.10.x/operations/backend_search/)

## 2. 배포 모드를 고르기

| 모드 | 선택 기준 | 근거 |
| --- | --- | --- |
| Monolithic | 공통 프로세스에서 구성 요소를 실행한다. 예제처럼 로컬 백엔드로 동작을 익히기 편하다 | [Tempo 배포 모드](https://grafana.com/docs/tempo/v2.10.x/set-up-for-tracing/setup-tempo/deploy/) · [Tempo v2.10.8 공식 예제](https://raw.githubusercontent.com/grafana/tempo/v2.10.8/example/docker-compose/local/tempo.yaml) |
| Microservices | 수집과 조회 등 구성 요소를 별도로 배포하고 확장한다. 여러 인스턴스가 같은 장기 보관 데이터를 읽을 수 있는 객체 스토리지를 사용한다 | [Tempo 배포 모드](https://grafana.com/docs/tempo/v2.10.x/set-up-for-tracing/setup-tempo/deploy/) · [Tempo 2.10 아키텍처](https://grafana.com/docs/tempo/v2.10.x/introduction/architecture/) |

## 3. Tempo 3.0 전환 시 확인할 경계

이 문서 묶음의 Ingester와 Compactor는 2.10 classic 기준이다. Tempo 3.0의 분산 모드에서는 Distributor가 Kafka에 기록하고 Block Builder와 Live Store가 이를 소비한다. 저장 블록의 컴팩션과 보존 기간은 Backend Scheduler와 Backend Worker가 담당한다. [Tempo 3.0 마이그레이션](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
