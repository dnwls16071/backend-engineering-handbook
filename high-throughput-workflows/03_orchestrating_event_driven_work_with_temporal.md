# Orchestrating Event-Driven Work with Temporal

Kafka가 주문 사실을 전달하면 Temporal이 수신 이후의 단계·시도·타이머를 기록하고 재개한다. 단계의 DB나 HTTP 부수 효과는 Activity에서 실행한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Workflows](https://docs.temporal.io/workflows) · [Temporal · Activities](https://docs.temporal.io/activities)

## 1. 시작과 실행을 분리한다

리스너는 결정적 Workflow ID로 시작 요청을 보내고 수락 여부를 확인한다. Workflow Worker는 이력을 바탕으로 진행을 재현한다. Activity Worker는 결과 저장이나 외부 호출 같은 작업을 수행한다. [Temporal Java · Workflow Basics](https://docs.temporal.io/develop/java/workflows/basics) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [Temporal · Task Queues](https://docs.temporal.io/task-queue) · [Temporal · Activities](https://docs.temporal.io/activities)

## 2. 장애 경계마다 멱등 키를 사용한다

Kafka 오프셋을 커밋하기 전에 리스너가 종료되면 같은 이벤트로 시작을 다시 시도할 수 있다. Activity도 부수 효과를 남긴 뒤 결과 보고가 유실되면 반복될 수 있다. Workflow 시작과 업무 쓰기에 각각 중복 보호가 필요하다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Temporal · Workflow ID and Run ID](https://docs.temporal.io/workflow-execution/workflowid-runid) · [Temporal · Activities](https://docs.temporal.io/activities)
