# Configuring Temporal Workers in Spring Boot

Temporal 연결, WorkflowClient, WorkerFactory를 Spring 빈으로 구성한다. 서버 주소와 namespace는 환경을 통해 바꾸고, 리스너와 Worker가 같은 Task Queue 이름을 사용한다. [Temporal SDK 1.31.0 · WorkerFactory](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/worker/WorkerFactory.java) · [Temporal SDK 1.31.0 · WorkflowClient](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/client/WorkflowClient.java) · [Temporal · Task Queues](https://docs.temporal.io/task-queue)

## 1. Worker를 등록한 뒤 시작한다

TemporalConfig.kt를 추가한다. 로컬 개발 서버는 7233의 gRPC와 default namespace를 사용한다. 종료 시 WorkerFactory가 폴링을 중지하고 연결 빈이 정리된다. 운영에서는 실행 중 Activity의 종료 유예, TLS·인증, 별도 namespace를 환경에 맞춰 적용한다. [Temporal CLI · Server](https://docs.temporal.io/cli/command-reference/server) · [Temporal SDK 1.31.0 · WorkerFactory](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/worker/WorkerFactory.java) · [Temporal SDK 1.31.0 · WorkflowServiceStubs](https://raw.githubusercontent.com/temporalio/sdk-java/v1.31.0/temporal-serviceclient/src/main/java/io/temporal/serviceclient/WorkflowServiceStubs.java)

```kotlin
// TemporalConfig.kt
package workflowlab

import io.temporal.client.WorkflowClient
import io.temporal.client.WorkflowClientOptions
import io.temporal.serviceclient.WorkflowServiceStubs
import io.temporal.serviceclient.WorkflowServiceStubsOptions
import io.temporal.worker.WorkerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

const val ORDER_QUEUE = "order-processing"

@Configuration
class TemporalConfig {
    @Bean(destroyMethod = "shutdown")
    fun temporalStubs(
        @Value("\${TEMPORAL_TARGET:127.0.0.1:7233}") target: String,
    ): WorkflowServiceStubs = WorkflowServiceStubs.newServiceStubs(
        WorkflowServiceStubsOptions.newBuilder().setTarget(target).build(),
    )

    @Bean
    fun temporalClient(
        stubs: WorkflowServiceStubs,
        @Value("\${TEMPORAL_NAMESPACE:default}") namespace: String,
    ): WorkflowClient = WorkflowClient.newInstance(
        stubs, WorkflowClientOptions.newBuilder().setNamespace(namespace).build(),
    )

    @Bean(initMethod = "start", destroyMethod = "shutdown")
    fun orderWorkerFactory(client: WorkflowClient, activities: OrderActivitiesImpl): WorkerFactory {
        val factory = WorkerFactory.newInstance(client)
        val worker = factory.newWorker(ORDER_QUEUE)
        worker.registerWorkflowImplementationTypes(OrderWorkflowImpl::class.java)
        worker.registerActivitiesImplementations(activities)
        return factory
    }
}
```
