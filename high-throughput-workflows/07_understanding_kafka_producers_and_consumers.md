# Understanding Kafka Producers and Consumers

프로듀서는 레코드를 파티션으로 보내고 브로커의 결과를 받는다. 컨슈머는 그룹 안에서 할당된 파티션을 읽고 재시작 지점인 오프셋을 관리한다. [Apache Kafka 4.3 · Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Apache Kafka 4.3 · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)

## 1. 프로듀서의 전송 결과와 재시도를 해석한다

acks=all은 현재 ISR의 응답을 기다리는 설정이다. 최소 ISR 조건과 복제 수가 내구성에 함께 작용한다. enable.idempotence는 해당 프로듀서의 재시도 중복을 억제하며, 애플리케이션이 별도의 전송 요청으로 같은 업무 이벤트를 발행하는 경우는 업무 키로 처리한다. [Apache Kafka 4.3 · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/)

## 2. 컨슈머 그룹에서 느린 처리를 격리한다

같은 그룹의 활성 처리 병렬성은 할당 가능한 파티션 수의 영향을 받는다. 작업을 오래 실행하느라 poll 간격 한도를 넘으면 재할당이 발생할 수 있다. 이 예의 리스너는 Temporal에 시작을 요청하고 완료까지 기다리는 작업은 Worker에 둔다. [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal SDK 1.31.0 · WorkflowClient](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/client/WorkflowClient.java) · [Temporal · Task Queues](https://docs.temporal.io/task-queue)
