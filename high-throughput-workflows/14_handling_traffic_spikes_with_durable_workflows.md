# Handling Traffic Spikes with Durable Workflows

피크에서는 요청 접수량과 실제 작업 수행량을 분리한다. Kafka는 이벤트 전달을, Temporal Task Queue는 Workflow·Activity 작업을 Worker에 배정하는 매개를 맡는다. [AWS · Avoiding Insurmountable Queue Backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Task Queues](https://docs.temporal.io/task-queue)

## 1. 백로그가 회복되는 속도를 예측한다

예를 들어 작업 12,000건이 대기 중이고 실측 처리량이 초당 300건, 계속 들어오는 양이 초당 200건이면 순소진은 초당 100건이고 회복 시간은 약 120초다. 처리량이 유입량 이하라면 피크가 끝나거나 처리량을 높여야 적체가 줄어든다. [AWS · Avoiding Insurmountable Queue Backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/)

## 2. 하위 시스템이 감당할 동시성으로 제한한다

Worker를 늘리기 전에 Activity DB 연결 수와 외부 API 제한을 확인한다. 느린 외부 작업을 다른 Task Queue에 둬 자원을 따로 할당할 수 있다. Kafka lag, 대기 작업 연령, Schedule-to-Start 지연, Activity 실패율을 각각 관측한다. [Temporal · Task Queues](https://docs.temporal.io/task-queue) · [Temporal Java · Activity Timeouts](https://docs.temporal.io/develop/java/activities/timeouts) · [AWS · Avoiding Insurmountable Queue Backlogs](https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/)
