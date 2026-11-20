# Spring Batch Parallelism and Transaction Boundaries

병렬 처리 방식은 느린 구간과 재시작 단위를 보고 고른다. Reader가 DB에서 시간을 쓰는지, Processor가 연산을 하는지, Writer가 저장소에서 병목을 겪는지 단일 스레드 실행에서 먼저 측정한다. 같은 이름의 Multi-threaded Step도 5.2와 6.x의 새 청크 구현에서 실행 경계가 다르다.

## 1. Spring Batch 5.2의 세 가지 병렬화 방식

| 방식 | 무엇을 병렬로 실행하는가 | 트랜잭션과 공유 상태 |
| --- | --- | --- |
| Multi-threaded Step | `TaskExecutor`가 같은 Step의 여러 청크를 실행한다. | 청크별로 워커 스레드에서 트랜잭션을 연다. Reader·Processor·Writer 인스턴스를 공유할 수 있어 스레드 안전성과 출력 순서, 재시작 동작을 검증한다. |
| Partitioning | 서로 겹치지 않는 입력 범위를 별도 워커 StepExecution으로 실행한다. | 워커마다 청크 트랜잭션과 `ExecutionContext`를 둔다. `@StepScope` Reader가 자신의 파티션 경계만 읽는다. |
| `AsyncItemProcessor` + `AsyncItemWriter` | 워커가 항목별 변환을 하고 Writer가 `Future` 결과를 모아 기록한다. | 메인 Step의 청크 트랜잭션은 Processor의 워커 스레드로 전달되지 않는다. 변환에는 되돌릴 수 없는 외부 변경을 피하고 Writer의 DB 기록을 청크 트랜잭션에 둔다. |

[Spring Batch 5.2 · Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/5.2/scalability.html) · [AsyncItemProcessor API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemProcessor.html) · [AsyncItemWriter API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemWriter.html)

### Multi-threaded Step의 Reader 공유

`SynchronizedItemStreamReader`로 `read()` 호출을 직렬화할 수 있다. 이 래퍼가 Writer의 동시성이나 항목 커밋 순서까지 제어하지는 않는다. 재시작 시 같은 입력을 중복 처리하는 것이 허용되지 않는 작업은 독립적인 체크포인트를 가진 파티션 방식도 검토한다. [SynchronizedItemStreamReader API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/support/SynchronizedItemStreamReader.html)

### 파티션 구성과 재시작

입력 ID를 `[1, 1001)`과 `[1001, 2001)`처럼 겹치지 않는 범위로 나눈다. `Partitioner`가 안정적인 파티션 이름과 범위를 `ExecutionContext`에 넣고, 워커가 `id >= :startId AND id < :endId`로 조회한다. 재시작 동안 파티션 이름과 범위를 유지하고, 끝난 범위와 실패 범위의 출력이 중복되지 않는지 확인한다.

### 비동기 Processor의 실패 처리

`AsyncItemWriter`는 Future에서 결과를 얻어 유효한 항목을 실제 Writer에 전달한다. 변환 예외는 Future를 읽는 쓰기 단계에서 드러날 수 있다. `filterCount`나 `ItemProcessListener.onProcessError`가 동기 처리와 같은 정보를 제공한다고 가정하지 않는다. Worker가 자체 트랜잭션으로 변경을 커밋했다면 이후 Step의 롤백으로 그 변경을 되돌릴 수 없다. [AsyncItemProcessor API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemProcessor.html) · [AsyncItemWriter API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/integration/async/AsyncItemWriter.html)

## 2. Spring Batch 6.x에서 바뀐 실행 경계

6.x의 새 `ChunkOrientedStep`에서 Multi-threaded Step의 Reader와 Writer는 Step 스레드에서 순차 실행되고, Processor가 워커에서 병렬로 실행된다. 이 워커 또한 Step 스레드에 묶인 청크 트랜잭션에 참여하지 않는다. 버전 외에도 실제로 사용하는 Step 구현과 Builder를 확인한다. [Spring Batch 6 · New Concurrency Model](https://github.com/spring-projects/spring-batch/blob/v6.0.3/spring-batch-docs/modules/ROOT/pages/whatsnew.adoc) · [Spring Batch 6 · Scaling and Parallel Processing](https://github.com/spring-projects/spring-batch/blob/v6.0.3/spring-batch-docs/modules/ROOT/pages/scalability.adoc)

워커에서 청크 전체를 처리해야 하면 6.x의 Local Chunking을 검토할 수 있다. 이 경우 위임된 청크 처리기가 트랜잭션과 Retry·Skip 정책을 책임진다. 기존 Multi-threaded Step을 옮길 때에는 DB 커밋 위치, Reader 상태, 재시작 범위를 같은 장애 시나리오로 다시 확인한다.

## 3. 처리량과 정합성을 함께 검증하기

같은 입력으로 초당 처리량, 청크 지연, 커넥션 풀 대기, 워커 큐를 비교한다. 특정 워커의 처리 실패를 재현하고 재실행 뒤 누락·중복과 완료 상태를 조회한다. 출력 순서가 업무 계약이면 병렬 실행에 맡기지 않고 결과를 별도로 정렬한다. 스레드 수를 늘릴 때는 DB 커넥션, 잠금 경합, 외부 호출 한도가 수용하는 동시성을 넘지 않게 한다.

관련 문서 [Spring Batch Parallel Processing](10_spring_batch_parallel_processing.md) · [Spring Batch Execution Metadata and Transaction Boundaries](13_spring_batch_execution_metadata_and_transaction_boundaries.md)
