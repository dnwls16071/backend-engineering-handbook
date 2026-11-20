# Spring Batch Job Launching, Operations, and Flow Control

카탈로그 Job 하나를 CLI, 애플리케이션 시작, REST에서 실행하는 상황을 기준으로 정리한다. 진입점은 Job 이름과 파라미터를 전달하고, Job은 Step 사이의 진행 경로를 정의한다. 실행과 조회, 재시작은 공유 메타데이터를 기준으로 판단한다.

## 1. Job과 메타데이터 저장소

| 구성 | 역할 |
| --- | --- |
| `Job`과 `JobInstance` | Job은 실행할 단계의 정의다. Job 이름과 식별 파라미터로 업무 실행 단위인 인스턴스가 정해진다. |
| `JobExecution`과 `StepExecution` | Job 실행 시도와 단계별 상태·건수를 기록한다. 재시작하면 같은 인스턴스에 새 JobExecution이 생긴다. |
| `JobRepository` | 실행 생성·갱신과 체크포인트를 관리한다. JDBC 구성에서는 `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION` 등을 사용한다. |
| `JobExplorer`와 `JobRegistry` | Explorer는 저장된 실행을 조회한다. Registry는 이름으로 실행할 Job 정의를 찾는다. |

여러 진입점에서 같은 기준일과 실행 모드를 보낼 때는 같은 저장소와 식별 규칙을 사용한다. 예를 들어 `businessDate`와 `mode`를 식별 값으로 두면 같은 날짜의 검증 전용 실행과 전체 적재 실행을 구분할 수 있다. [Spring Batch 5.2 · Domain Language](https://docs.spring.io/spring-batch/reference/5.2/domain.html) · [Advanced Metadata Usage](https://docs.spring.io/spring-batch/reference/5.2/job/advanced-meta-data.html)

## 2. 실행 진입점과 Spring Boot 자동 구성

| 진입점 | 실행 방식 |
| --- | --- |
| 독립 CLI | `CommandLineJobRunner`가 Spring 컨텍스트를 로드하고 Job 이름과 인자를 `JobParameters`로 읽어 `JobLauncher`에 넘긴다. 스케줄러는 프로세스 종료 코드도 확인할 수 있다. |
| Spring Boot 시작 | Batch 자동 구성이 켜져 있을 때 단일 Job 빈은 시작 시 자동 실행된다. 여러 Job 가운데 실행 대상을 `spring.batch.job.name`으로 지정할 수 있다. |
| 서비스나 REST | 애플리케이션에서 `JobLauncher.run(job, parameters)` 또는 `JobOperator`를 호출한다. REST 전용 서비스는 `spring.batch.job.enabled=false`로 시작 시 자동 실행을 끌 수 있다. |

Spring Boot에서 `@EnableBatchProcessing`을 추가하거나 `DefaultBatchConfiguration`을 확장하면 Batch 자동 구성이 물러난다. 이 경우 Boot의 배치 스키마 초기화 지원도 비활성화되므로, 저장소와 스키마를 관리하는 경로를 명시한다. [Spring Batch 5.2 · Running a Job](https://docs.spring.io/spring-batch/reference/5.2/job/running.html) · [Spring Boot 3.4 · Batch Applications](https://docs.spring.io/spring-boot/3.4/how-to/batch.html)

## 3. REST에서 실행 ID로 제어한다

| 요청 예 | Spring Batch 5.2에서 연결할 동작 |
| --- | --- |
| `POST /batch/jobs/catalog/runs` | `JobOperator.start(jobName, properties)`로 새 인스턴스를 시작한다. 동일 식별값이 이미 있으면 기존 실행을 안내하거나 충돌로 응답하는 계약을 둔다. |
| `GET /batch/executions/{id}` | `JobExplorer.getJobExecution(id)`로 저장된 상태를 읽는다. 실행 ID, 상태, 시작·종료 시각과 단계 요약을 제공한다. |
| `POST /batch/executions/{id}/restart` | 실패하거나 중지된 실행에 `JobOperator.restart(id)`를 호출하고 새 실행 ID를 반환한다. |
| `POST /batch/executions/{id}/stop` | `JobOperator.stop(id)`로 중지를 요청한다. 실제 `STOPPED` 상태는 실행 조회에서 확인한다. |

오래 걸리는 실행을 요청 스레드에서 기다리지 않으려면 `TaskExecutorJobLauncher`에 비동기 실행기를 구성한다. 접수가 성공하면 `202 Accepted`와 실행 ID, 상태 조회 주소를 반환할 수 있다. 작업 결과는 이후 조회로 확인한다. 실행 가능한 Job과 파라미터를 서버에서 검증하고 실행·조회·중지 권한을 구분한다. [Spring Batch 5.2 · Configuring a JobLauncher](https://docs.spring.io/spring-batch/reference/5.2/job/configuring-launcher.html) · [Advanced Metadata Usage](https://docs.spring.io/spring-batch/reference/5.2/job/advanced-meta-data.html) · [RFC 9110 · 202 Accepted](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted)

## 4. Flow에 분기와 종료 조건을 둔다

아래 Job은 입력 검사에 성공한 뒤 실행 모드를 읽는다. `validate`는 검사만 하고 종료하며, `full`은 적재 Step까지 실행한다. Step에서 `on(...)`은 `ExitStatus`를 매칭한다. Decider에서는 `FlowExecutionStatus`를 반환해 흐름을 선택한다. [Spring Batch 5.2 · Controlling Step Flow](https://docs.spring.io/spring-batch/reference/5.2/step/controlling-flow.html)

```java
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.job.flow.FlowExecutionStatus;
import org.springframework.batch.core.job.flow.JobExecutionDecider;
import org.springframework.batch.core.repository.JobRepository;

public class CatalogJobFlow {
    public static Job create(JobRepository jobs, Step validate, Step load) {
        JobExecutionDecider mode = (execution, lastStep) -> {
            String requested = execution.getJobParameters().getString("mode", "");
            return new FlowExecutionStatus(switch (requested) {
                case "validate" -> "VALIDATE_ONLY";
                case "full" -> "LOAD";
                default -> "INVALID_MODE";
            });
        };

        return new JobBuilder("catalogOperations", jobs)
                .start(validate).on("COMPLETED").to(mode)
                .from(validate).on("*").fail()
                .from(mode).on("VALIDATE_ONLY").end()
                .from(mode).on("LOAD").to(load)
                .from(mode).on("*").fail()
                .from(load).on("COMPLETED").end()
                .from(load).on("*").fail()
                .end()
                .build();
    }
}
```

전이의 `end()`는 Job을 완료 상태로 끝내므로 동일 인스턴스에서 재시작할 필요가 없는 경로에 쓴다. `fail()`은 실패를 기록하고 재시작 규칙을 적용할 수 있게 한다. 운영 확인을 위해 의도적으로 중단하고 다시 시작할 Step을 지정할 때는 `stopAndRestart(...)`를 쓸 수 있다. [Spring Batch 5.2 · Controlling Step Flow](https://docs.spring.io/spring-batch/reference/5.2/step/controlling-flow.html) · [Spring Batch Flow and Conditional Transitions](04_spring_batch_flow_and_conditional_transitions.md)

[Docker의 PostgreSQL 메타데이터 저장소](13_spring_batch_execution_metadata_and_transaction_boundaries.md#3-docker의-postgresql에서-실행-기록-읽기)에서 검증 전용 실행과 전체 실행을 시작한다. 전체 실행의 적재 단계에 실패를 넣고, 원인을 제거한 뒤 기존 실행 ID로 재시작한다. `JobExplorer`로 단계 목록과 실행 상태를 읽어 검증 전용 실행에 적재 이력이 생기지 않았는지, 재시작은 같은 인스턴스의 새 실행인지 확인한다.

Spring Batch 5.2.2와 PostgreSQL 17로 검증했다. 비동기 시작은 검증 Step이 끝나기 전에 실행 ID를 반환했고, 동일 파라미터의 새 실행은 거절됐다. 실패한 전체 적재를 기존 실행 ID로 재시작하자 같은 JobInstance에 새 실행이 생겼으며, 검증 Step은 건너뛰고 적재 Step만 완료했다.

관련 문서 [Spring Batch Job Configuration and Execution](02_spring_batch_job_configuration_and_execution.md) · [Spring Batch Testing and Operations](12_spring_batch_testing_and_operations.md)
