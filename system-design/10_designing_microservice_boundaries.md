# Designing Microservice Boundaries

마이크로서비스 경계는 배포 단위의 수보다 업무 책임, 데이터를 확정하는 주체, 변경 주기로 정한다. 주문과 PG 승인은 각각 다른 서비스가 확정하는 업무 사실이다. [Microsoft Microservice Boundaries](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries) · [AWS Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 1. 팀과 데이터의 소유권을 명시한다

주문이 이행 상태를, 결제가 승인·취소 기록을, 재고가 가용량과 예약을 소유하는 예다. 서비스 사이의 읽기 계약과 이벤트를 통해 상태를 참조한다. 독립 배포나 확장 이점이 작으면 모듈 간 경계부터 검증할 수 있다. [Microsoft Microservice Boundaries](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries)

## 2. 동기 호출과 비동기 변경의 계약을 정한다

동기 호출은 요청 기한과 결과를 즉시 알아야 하는 경로에 둔다. 비동기로 상태를 전달할 때는 로컬 변경과 Outbox를 함께 저장하고, 소비자가 이벤트 ID와 업무 상태를 확인한다. 여러 단계에서 실패할 경우 완료 상태와 보상 상태를 분리한다. [AWS Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS Backoff and Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

## 3. 운영 비용과 복구 동작을 확인한다

서비스 간 지연, 실패율, 큐 체류와 운영 책임 범위를 설계에 포함한다. 결제 응답 유실과 이벤트 중복을 주입해 이전 상태를 잘못 덮어쓰지 않고 정상 경로와 같은 결과로 수렴하는지 본다. [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
