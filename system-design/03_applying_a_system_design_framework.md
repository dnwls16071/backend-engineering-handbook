# Applying a System Design Framework

설계안은 사용자가 할 수 있는 일, 어떤 응답을 성공이라 볼지, 어떤 조건에서 속도나 일관성을 양보할지부터 작성한다. [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/) · [Microsoft Microservice Boundaries](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries)

## 1. 범위와 성능 목표를 좁힌다

예를 들어 게시글 쓰기·상세 조회만 1차 범위로 정한다. 작성자가 작성 직후 자기 글을 봐야 한다면 읽기 경로에도 그 요구를 명시한다. 추천 목록과 검색은 각자의 최신성 허용 시간을 정할 수 있다. [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 2. API·모델·정상 경로를 먼저 맞춘다

POST 요청의 재전송과 중복 생성 정책, GET의 반환 모델, 원본 식별자를 정한다. 먼저 요청이 API와 DB를 통과하는 흐름을 그린 후, 캐시나 비동기 저장소를 추가해도 쓰기 성공의 의미가 유지되는지 비교한다. [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 병목과 실패를 한 가지씩 대입한다

쓰기 타임아웃, 읽기 복제 지연, 인기 키 만료, DB 장애를 각각 대입한다. 무엇이 이미 커밋됐는지, 사용자가 어떤 상태를 보는지, 어떤 키로 대조하거나 재시도하는지를 기록한다. [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html) · [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/)

마지막에는 설계 선택, 검증할 부하 조건, 알려진 한계를 짧게 남긴다. 수치 추정과 SLO를 연결해 어떤 측정 결과에서 다음 확장안을 검토할지 정한다. [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
