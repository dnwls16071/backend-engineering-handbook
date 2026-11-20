# Spring Batch Domain Model

## 1. 작업 정의와 실행 기록

Spring Batch는 배치 작업의 정의, 입력으로 구별한 작업 단위, 실행 시도를 각각 기록한다. 예를 들어 카탈로그 가져오기 작업을 같은 파일과 기준일로 재시작하면, 같은 `JobInstance` 안에 새 `JobExecution`이 생길 수 있다. [Spring Batch 5.2 · Domain Language](https://docs.spring.io/spring-batch/reference/5.2/domain.html)

| 객체 | 카탈로그 가져오기에서의 의미 |
| --- | --- |
| `Job` | 입력 검사, 가져오기, 대사를 어떤 순서로 실행할지 정의한다. |
| `JobParameters` | 기준일, 입력 파일 경로 등 실행에 전달할 값을 담는다. |
| `JobInstance` | Job 이름과 식별 파라미터의 조합으로 구별하는 논리 작업이다. |
| `JobExecution` | 작업을 실행한 한 번의 시도다. 상태와 시작·종료 시각을 기록한다. |
| `Step` | 입력 검사나 파일 가져오기처럼 Job의 한 단계를 정의한다. |
| `StepExecution` | 한 단계의 실행 시도다. 결과 상태와 읽기·쓰기·스킵 건수 등을 기록한다. |

기준일과 입력 파일 경로를 식별 파라미터로 두고, 요청자 ID는 운영 기록용 비식별 파라미터로 둘 수 있다. 실패한 작업을 재시작할 때는 같은 식별 값을 사용하고, 체크포인트에 대응하는 입력의 내용과 순서를 유지한다. [Spring Batch 5.2 · JobParameters와 JobInstance](https://docs.spring.io/spring-batch/reference/5.2/domain.html) · [재시작과 Job 실행](02_spring_batch_job_configuration_and_execution.md)

## 2. 실행 컨텍스트와 저장소

`ExecutionContext`에는 재시작 때 이어서 처리할 위치나 다음 단계에서 필요한 작은 값을 저장할 수 있다. Step 컨텍스트는 커밋 경계에서 저장되고, Job 컨텍스트는 단계 사이에서 저장된다. 예를 들어 CSV에서 처리한 위치는 해당 Step에, 다음 Step으로 넘길 결과 파일 위치는 Job 컨텍스트에 둘 수 있다. [Spring Batch 5.2 · ExecutionContext](https://docs.spring.io/spring-batch/reference/5.2/domain.html)

`JobLauncher`는 Job과 파라미터를 받아 실행을 시작한다. `JobRepository`는 실행 상태와 체크포인트의 생성 및 갱신을 담당한다. JDBC 저장소를 쓰면 `BATCH_JOB_INSTANCE`, `BATCH_JOB_EXECUTION`, `BATCH_STEP_EXECUTION`과 각 컨텍스트 테이블에서 기록을 조회할 수 있다. 사업 데이터의 저장소와 배치 메타데이터의 저장소를 구성할 때 각각의 트랜잭션 경계도 확인한다. [Spring Batch 5.2 · JobRepository](https://docs.spring.io/spring-batch/reference/5.2/job/configuring-repository.html) · [Spring Batch 5.2 · Metadata Schema](https://docs.spring.io/spring-batch/reference/5.2/schema-appendix.html)
