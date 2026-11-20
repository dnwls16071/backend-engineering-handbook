# Spring Batch Flow, Listeners, and Fault Tolerance

배치 운영에서 알고 싶은 것은 Job의 성공 여부뿐 아니라 어느 Step에서 항목이 제외됐고, 어디까지 커밋됐으며, 어느 실패가 남았는지다. Spring Batch 5.2에서 Flow는 진행 경로를, 리스너는 실행 관찰 시점을, Skip과 Retry는 오류 허용 범위를 정의한다.

## 1. 순차 실행, 분기, 데이터 전달

| 구성 | 카탈로그에 적용하는 방법 |
| --- | --- |
| 순차 흐름 | 준비 → 적재 → 대사처럼 앞 단계의 완료가 다음 단계의 조건일 때 연결한다. |
| 조건 분기 | `on(...)`은 Step의 `ExitStatus`를 매칭한다. 스킵이 발생한 성공은 `COMPLETED_WITH_SKIPS`로 표시해 검토 Step으로 보낼 수 있다. |
| 상태 기반 결정 | 다음 Step이 실행 지표나 업무 상태에 따라 달라지면 `JobExecutionDecider`에 조건을 둔다. |
| Split | 서로 독립적인 Flow를 `TaskExecutor`로 실행한다. 카탈로그 적재와 독립 파일 적재를 병렬로 실행하고, 모든 Flow의 결과를 모은 뒤 대사한다. |

Step에서 만든 결과는 DB나 파일로 기록하고 뒤 Step에는 키나 경로를 전달한다. 같은 Step의 재시작 위치는 `ItemStream`과 Step `ExecutionContext`로 관리한다. 다음 Step이 작은 값을 읽어야 한다면 `ExecutionContextPromotionListener`로 선택한 키를 Job 컨텍스트에 올릴 수 있다. 승격이 필요한 종료 상태를 명시하고, 병렬 브랜치가 같은 공유 키를 덮어쓰지 않게 한다. [Spring Batch 5.2 · Controlling Step Flow](https://docs.spring.io/spring-batch/reference/5.2/step/controlling-flow.html) · [Spring Batch 5.2 · Passing Data to Future Steps](https://docs.spring.io/spring-batch/reference/5.2/common-patterns.html)

## 2. 리스너의 호출 시점과 기록 범위

| 관찰 대상 | 5.2에서 확인할 시점 |
| --- | --- |
| Job과 Step | `JobExecutionListener`로 Job 시작·종료를, `StepExecutionListener`로 단계별 건수와 종료 코드를 관찰한다. |
| Chunk | `beforeChunk`는 트랜잭션 시작 뒤 읽기 전에, `afterChunk`는 성공한 청크의 커밋 뒤에 호출된다. 실패한 청크는 `afterChunkError`에서 관찰한다. |
| Item | 읽기·변환·쓰기 리스너는 항목 처리 시도를 관찰한다. `afterWrite`는 쓰기 이후이면서 커밋 전이다. |
| Skip | `SkipListener`로 최종 제외된 항목이나 읽기 오류를 별도 집계한다. |

Job 실행 ID, Step 실행 ID, 항목의 업무 키를 로그에서 연결한다. 커밋 전 콜백을 보고 완료 알림을 보내면 이후 롤백 때 외부 알림만 남을 수 있다. 실패 복구에 필요한 기록은 트랜잭션 경계를 확인하고, 커밋 후 알림도 별도의 발행 실패나 재실행에 대비한다. [Spring Batch 5.2 · Intercepting Step Execution](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/intercepting-execution.html)

## 3. Skip, Retry, 실패의 기준

| 상황 | 정책 | 검증할 결과 |
| --- | --- | --- |
| 규칙상 제외하는 정상 항목 | Processor가 `null`을 반환 | 필터 건수 증가 |
| 잘못된 입력 한 건 | 특정 예외만 한도 내에서 Skip | 제외 사유와 읽기·변환·쓰기 스킵 건수 확인 |
| 일시적 DB 잠금 오류 | 제한된 Retry와 백오프 | 성공하면 한 번만 출력에 반영 |
| 스키마 오류, Retry 소진 | 처리 가능한 별도 정책이 없으면 Step 실패 | 실패 범위, 롤백 건수와 재시작 지점 확인 |

5.2에서는 `faultTolerant()` 설정에 예외 분류와 한도를 붙인다. `skipLimit`는 읽기·변환·쓰기 스킵의 합계에 적용된다. 실패가 발생하면 재시도 중인 항목, 실제 제외된 항목, 커밋된 항목을 서로 다른 건수로 관찰한다. 포괄적인 예외를 모두 스킵하는 구성은 데이터 손실을 정상 종료처럼 보이게 할 수 있다. [Spring Batch 5.2 · Skip Logic](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/configuring-skip.html) · [Spring Batch 5.2 · Retry Logic](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/retry-logic.html)

관련 문서 [Spring Batch Flow and Conditional Transitions](04_spring_batch_flow_and_conditional_transitions.md) · [Spring Batch Execution Listeners](11_spring_batch_execution_listeners.md) · [Spring Batch Repeat, Retry, and Skip](09_spring_batch_repeat_retry_and_skip.md)
