# Spring Batch Job Configuration and Execution

## 1. 순차 Job 정의하기

`JobBuilder`는 Job 이름과 `JobRepository`를 받는다. `start()`로 시작 Step을 지정하고, 성공 뒤 순차적으로 실행할 단계는 `next()`로 이어 붙인다. 다음 예제는 카탈로그 입력 검사, 가져오기, 대사를 순서대로 실행한다. 검증기는 필수 파라미터의 이름이 있는지 확인한다. 날짜의 허용 범위나 입력 파일의 접근 가능 여부는 별도의 검증기로 다룰 수 있다. [Spring Batch 5.2 · Configuring a Job](https://docs.spring.io/spring-batch/reference/5.2/job/configuring.html)

```java
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.DefaultJobParametersValidator;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;

public class CatalogJobPlan {

    public static Job create(JobRepository jobs, Step prepare, Step load, Step reconcile) {
        var parameters = new DefaultJobParametersValidator(
                new String[]{"businessDate", "inputFile"}, new String[]{"requestedBy"});

        return new JobBuilder("catalogImport", jobs)
                .start(prepare)
                .next(load)
                .next(reconcile)
                .validator(parameters)
                .build();
    }
}
```

순차 Job에서는 Step이 실패하면 후속 Step으로 진행하지 않는다. 결과별로 다른 단계에 연결하려면 [조건 분기 Flow](04_spring_batch_flow_and_conditional_transitions.md)를 구성한다. [Spring Batch 5.2 · Controlling Step Flow](https://docs.spring.io/spring-batch/reference/5.2/step/controlling-flow.html)

## 2. 실행기와 재시작 조건

`JobLauncher.run(job, parameters)`가 호출되면 JobRepository가 동일한 [JobInstance](01_spring_batch_domain_model.md)의 실행 상태를 확인한다. 같은 인스턴스가 이미 실행 중이면 중복 실행을 거부한다. 예제처럼 식별 파라미터가 있는 Job은 완료한 인스턴스를 같은 식별 값으로 다시 실행하면 `JobInstanceAlreadyCompleteException`이 발생한다. 실패한 인스턴스는 Job과 Step의 재시작 정책에 따라 실행을 이어갈 수 있다. `preventRestart()`는 해당 Job을 재시작 불가로 정의한다. [Spring Batch 5.2 · Running a Job](https://docs.spring.io/spring-batch/reference/5.2/job/running.html) · [Spring Batch 5.2 · Restartability](https://docs.spring.io/spring-batch/reference/5.2/job/configuring.html)

`JobParametersIncrementer`는 다음 인스턴스에 사용할 파라미터를 정의한다. `RunIdIncrementer`의 식별 값이 증가하면 새 인스턴스가 된다. 같은 실패 건을 이어서 처리할 때는 원래 식별 값을 유지한다. 실행기에 비동기 `TaskExecutor`를 설정한 경우 반환한 실행 ID로 최종 결과를 별도로 조회한다. [Spring Batch 5.2 · Running a Job](https://docs.spring.io/spring-batch/reference/5.2/job/running.html) · [Spring Batch 5.2 · Advanced Metadata Usage](https://docs.spring.io/spring-batch/reference/5.2/job/advanced-meta-data.html)
