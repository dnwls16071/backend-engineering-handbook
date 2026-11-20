# Spring Batch Parallel and Distributed Processing

Spring Batch 5.2에서 병렬화할 단위를 기준으로 실행 방식을 고른다. 상품 적재를 예로, 청크·입력 범위·독립 Flow·항목 변환 중 어디가 느린지 확인한 뒤 처리량과 재시작 결과를 함께 비교한다.

## 1. 병렬화 단위와 실행 위치

| 방식 | 나누는 단위 | 읽기·처리·쓰기 위치 |
| --- | --- | --- |
| Multi-threaded Step | 한 Step의 청크 | 같은 JVM의 워커 스레드가 청크를 처리한다. Reader·Processor·Writer가 공유될 수 있다. |
| Local Partitioning | 겹치지 않는 입력 범위 | 같은 JVM의 워커 Step이 범위별로 읽고 처리하고 쓴다. |
| Remote Partitioning | 겹치지 않는 입력 범위 | 다른 프로세스의 워커 Step이 자기 범위를 직접 읽고 처리하고 쓴다. |
| Remote Chunking | 매니저가 읽은 항목 묶음 | 매니저가 입력을 읽고 브로커로 청크를 보낸다. 원격 워커가 처리하고 쓴다. |
| Parallel Steps | 서로 독립적인 Flow | 같은 JVM에서 Flow별 Step을 실행하고 모두 끝난 뒤 다음 단계로 진행한다. |
| `AsyncItemProcessor` | 개별 항목의 변환 | Step이 읽고, 워커 스레드가 변환한다. `AsyncItemWriter`가 결과를 모아 쓴다. |

Multi-threaded Step에서는 청크 완료 순서와 공유 컴포넌트의 안전성을 확인한다. Reader의 `read()`를 동기화해도 출력 순서, Writer의 안전성, 체크포인트 동작은 각각 검증해야 한다. Spring Batch 6의 새 청크 구현에서는 실행 위치가 달라지므로 사용하는 버전과 Builder를 먼저 확인한다. [Spring Batch 5.2 · Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/5.2/scalability.html) · [버전별 트랜잭션 경계](16_spring_batch_parallelism_and_transaction_boundaries.md)

## 2. Local Partitioning에서 실패한 범위만 이어서 처리한다

상품 ID 1부터 9까지를 겹치지 않는 세 범위로 나눈다. 아래 `Partitioner`를 [로컬 매니저 Step 구성](10_spring_batch_parallel_processing.md#2-파티션마다-입력-범위와-상태-분리하기)에 전달하고 `gridSize`를 3으로 지정한다. 실제 동시 실행 수는 `TaskExecutor`의 스레드 수와 자원 한도에 맞춘다.

```java
import java.util.Map;
import org.springframework.batch.core.partition.support.Partitioner;
import org.springframework.batch.item.ExecutionContext;

public class CatalogRangePartitioner implements Partitioner {
    @Override
    public Map<String, ExecutionContext> partition(int gridSize) {
        return Map.of(
                "range-01", range(1, 4),
                "range-02", range(4, 7),
                "range-03", range(7, 10));
    }

    private static ExecutionContext range(long startId, long endId) {
        var context = new ExecutionContext();
        context.putLong("startId", startId);
        context.putLong("endId", endId);
        return context;
    }
}
```

워커 Reader는 `@StepScope`에서 `stepExecutionContext`의 시작·끝 ID를 받아 `id >= :startId AND id < :endId`로 조회한다. 각 워커의 청크 트랜잭션과 체크포인트는 해당 워커 StepExecution에 연결된다. 재시작할 때는 원본과 파티션 이름·경계를 보존한다. 범위를 재분배하려면 기존 체크포인트의 의미가 바뀌는지 확인하고 새 실행으로 관리할지 결정한다. [Spring Batch 5.2 · Partitioning](https://docs.spring.io/spring-batch/reference/5.2/scalability.html) · [Late Binding](https://docs.spring.io/spring-batch/reference/5.2/step/late-binding.html)

## 3. 원격 파티션과 원격 청킹의 경계를 고른다

**Remote Partitioning**에서 매니저는 Job·Step 실행 ID가 포함된 `StepExecutionRequest`를 보낸다. 워커는 공유 메타데이터에서 파티션 컨텍스트를 읽어 입력 범위를 직접 처리한다. 매니저는 응답 채널 또는 JobRepository 폴링으로 실행 결과를 수집한다. 파일과 DB 입력을 워커별로 독립적으로 읽을 수 있을 때 적용할 수 있다. [Spring Batch 5.2 · Remote Partitioning](https://docs.spring.io/spring-batch/reference/5.2/spring-batch-integration/sub-elements.html#remote-partitioning)

**Remote Chunking**에서는 매니저의 Reader가 읽은 항목을 청크 요청으로 발행한다. 워커가 Processor와 Writer를 실행하고 처리 정보를 응답으로 보낸다. 큐의 내구성, 전달 및 타임아웃 처리, 워커 중단 뒤 중복 요청의 결과를 점검한다. 읽기가 주 병목이면 워커를 늘려도 매니저의 읽기 처리량이 먼저 한계에 도달할 수 있다. [Spring Batch 5.2 · Remote Chunking](https://docs.spring.io/spring-batch/reference/5.2/spring-batch-integration/sub-elements.html#remote-chunking)

원격 워커의 응답이 유실되더라도 업무 데이터가 이미 커밋됐을 수 있다. 실행 ID와 업무 키로 결과를 대조하고, 재요청되어도 동일 업무 키의 결과가 중복되지 않도록 한다. 브로커 전달 확인과 업무 DB 커밋은 각자 관찰한다. [Spring Batch 5.2 · Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/5.2/scalability.html)

## 4. Parallel Steps와 비동기 Processor의 적용 범위

파일 상품 적재와 독립된 가격 대사처럼 경합이나 선행 의존성 없이 진행할 수 있는 Flow는 `split(taskExecutor)`로 나눌 수 있다. Job은 모든 병렬 Flow의 결과를 모은 뒤 후속 단계로 전이한다. 한 Step의 값이 다른 Step의 입력이라면 의존성을 Flow 순서에 표현한다. [Spring Batch 5.2 · Parallel Steps](https://docs.spring.io/spring-batch/reference/5.2/scalability.html)

`AsyncItemProcessor`는 항목 변환을 실행기에 넘기고 `Future`를 반환한다. `AsyncItemWriter`는 결과를 기다렸다가 실제 Writer에 전달한다. 변환 스레드에서 한 DB 변경은 Step의 청크 트랜잭션에 자동으로 참여하지 않는다. 변환 예외는 Writer가 Future를 가져오는 시점에 나타날 수 있으므로, 동기 처리의 `filterCount`나 `onProcessError`와 동일한 관측을 기대하지 않는다. [AsyncItemProcessor API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemProcessor.html) · [AsyncItemWriter API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemWriter.html)

## 5. 처리량과 복구 결과를 함께 비교한다

- 단일 스레드 기준으로 읽기·변환·쓰기 시간과 초당 처리량을 기록한다. 병렬화 후에는 파티션별 완료 시간, DB 커넥션 대기, 워커 큐 지연도 비교한다.
- [Docker의 PostgreSQL](13_spring_batch_execution_metadata_and_transaction_boundaries.md#3-docker의-postgresql에서-실행-기록-읽기)에서 가운데 파티션의 마지막 청크만 실패시킨다. 동일 JobInstance를 재시작해 완료한 파티션이 다시 실행되지 않고 실패한 워커가 체크포인트부터 이어가는지 확인한다.
- 원격 구성에서는 메시지 재전달, 워커 중단, 응답 유실을 각각 재현하고 최종 업무 키 목록을 기준으로 누락과 중복을 검증한다.

Spring Batch 5.2.2와 PostgreSQL 17에서 상품 6의 쓰기 직후 오류를 발생시켰다. 첫 실행은 상품 여덟 건을 커밋했다. 재시작에서는 완료한 두 파티션을 건너뛰고 실패한 파티션이 상품 6만 기록해, 최종 테이블에 고유 상품 아홉 건이 남았다.
