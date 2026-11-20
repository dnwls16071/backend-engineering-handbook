# Spring Batch Parallel Processing

## 1. 어디에서 작업을 나눌지 정하기

| 구성 | 작업을 나누는 단위 |
| --- | --- |
| `AsyncItemProcessor`와 `AsyncItemWriter` | 프로세서의 항목별 작업을 실행기에 맡기고 Writer에서 결과를 모은다. |
| Multi-threaded Step | Spring Batch 5.2에서 같은 Step의 청크를 여러 스레드에서 실행한다. |
| Parallel Steps | 서로 독립적인 Flow를 `split(...)`으로 병렬 실행한다. |
| Partitioning | 입력을 범위별로 나눠 각 파티션을 별도의 StepExecution에서 처리한다. |

먼저 읽기, 변환, 쓰기 중 실제로 시간이 오래 걸리는 부분을 측정한다. 처리 순서와 Reader 상태를 함께 관리해야 하는 작업은 범위별로 독립된 파티션으로 나눌 수 있다. `AsyncItemProcessor`는 변환 결과를 `Future`로 반환하며, 래퍼의 특성상 프로세서 오류 리스너나 필터 건수의 관측이 일반 청크와 다를 수 있다. [Spring Batch 5.2 · Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/5.2/scalability.html) · [Spring Batch 5.2.2 API · AsyncItemProcessor](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemProcessor.html)

## 2. 파티션마다 입력 범위와 상태 분리하기

예제는 준비한 `Partitioner`와 워커 Step을 로컬 실행기에 연결한다. `Partitioner`는 파티션 이름을 키로, 입력 파일 또는 시작·종료 키를 담은 `ExecutionContext`를 값으로 반환한다. 워커는 `@StepScope`에서 그 값을 읽는다. 재시작할 수 있도록 파티션 이름과 입력 범위를 안정적으로 유지한다. [Spring Batch 5.2 · Partitioning](https://docs.spring.io/spring-batch/reference/5.2/scalability.html)

```java
import org.springframework.batch.core.Step;
import org.springframework.batch.core.partition.support.Partitioner;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.core.task.TaskExecutor;

public class CatalogPartitions {

    public static Step manager(JobRepository jobs, Step worker, Partitioner ranges, TaskExecutor executor) {
        return new StepBuilder("catalogPartitionManager", jobs)
                .partitioner(worker.getName(), ranges)
                .step(worker)
                .gridSize(4)
                .taskExecutor(executor)
                .build();
    }
}
```

`gridSize(4)`는 작업 분할에 전달하는 설정값이다. 실제 동시성은 실행기의 스레드 수, 대기열, 데이터베이스 커넥션 한도에도 좌우된다. 서로 다른 파티션이 같은 출력을 덮어쓰지 않게 범위를 나눈다. [Spring Batch 5.2 · PartitionHandler와 자원 관리](https://docs.spring.io/spring-batch/reference/5.2/scalability.html)

## 3. 공유 상태와 재시작 확인하기

Multi-threaded Step에서는 항목의 완료 순서가 달라질 수 있다. `SynchronizedItemStreamReader`는 Reader의 `read()` 호출을 동기화한다. Writer의 스레드 안전성, 순서, 체크포인트를 따로 확인해야 하며, 일부 Reader에서는 동기화 래퍼와 재시작을 같이 사용하기 까다로울 수 있다. 파티션에서는 각 StepExecution에 개별 Reader와 체크포인트를 둘 수 있다. [Spring Batch 5.2 · Multi-threaded Step](https://docs.spring.io/spring-batch/reference/5.2/scalability.html) · [Spring Batch 5.2.2 API · SynchronizedItemStreamReader](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/support/SynchronizedItemStreamReader.html)
