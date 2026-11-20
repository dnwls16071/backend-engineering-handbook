# Spring Batch Database Pipelines and Scheduling

DB 기반 청크 Step을 구성할 때는 읽기 방식, 변환과 필터링, 출력 트랜잭션, 실행에 쓰는 기준일을 먼저 정한다. 예약 실행과 수동 재시작이 같은 파라미터 및 입력 계약을 사용하도록 구성한다. [Spring Batch 5.2 · Database Readers and Writers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/database.html)

## 1. Cursor Reader와 Paging Reader

| Reader | 동작 | 확인할 내용 |
| --- | --- | --- |
| `JdbcCursorItemReader` | 커서를 열고 결과 집합에서 다음 행을 읽는다. | 연결이 오래 유지된다. fetch size와 실제 가져오기 방식은 JDBC 드라이버와 설정에 따라 확인한다. |
| `JdbcPagingItemReader` | 정렬 키를 기준으로 페이지마다 새 쿼리를 실행한다. | 정렬 키에 유일 제약을 두고, 재시작 시에도 정렬 키와 조회 범위를 안정적으로 유지한다. |

청크 크기는 커밋 간격이고, 페이지 크기는 읽기 쿼리의 단위다. 두 크기는 별도 설정이며 같은 크기부터 측정해 볼 수 있다. 읽는 동안 원본의 정렬 키나 조회 대상이 바뀌면 누락이나 중복이 생길 수 있다. 기준일, 입력 버전 또는 상한 키를 정해 그 실행의 입력 집합을 보존한다.

## 2. 기준일 파라미터로 Reader를 구성하기

예제는 `catalog_source`에 `id bigint PRIMARY KEY`, `business_date date NOT NULL`, `sku`, `price_cents`가 있다고 가정한다. 컨테이너의 PostgreSQL에 연결한 `DataSource`로 기준일에 해당하는 행을 읽는다. `@StepScope`는 Step이 실행될 때 파라미터를 평가하고, 반환 타입의 `ItemStream` 계약으로 열기·체크포인트 갱신·닫기를 연결한다. [Spring Batch 5.2 · Late Binding](https://docs.spring.io/spring-batch/reference/5.2/step/late-binding.html)

```java
import java.time.LocalDate;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.batch.core.configuration.annotation.StepScope;
import org.springframework.batch.item.database.JdbcPagingItemReader;
import org.springframework.batch.item.database.Order;
import org.springframework.batch.item.database.builder.JdbcPagingItemReaderBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
public class CatalogPagingConfiguration {
    public record SourceRow(long id, String sku, long priceCents) {}

    @Bean
    @StepScope
    JdbcPagingItemReader<SourceRow> catalogSourceReader(
            DataSource source, @Value("#{jobParameters['businessDate']}") String businessDate) {
        return new JdbcPagingItemReaderBuilder<SourceRow>()
                .name("catalogSourceReader")
                .dataSource(source)
                .selectClause("select id, sku, price_cents")
                .fromClause("from catalog_source")
                .whereClause("where business_date = :businessDate")
                .parameterValues(Map.of("businessDate", LocalDate.parse(businessDate)))
                .sortKeys(Map.of("id", Order.ASCENDING))
                .pageSize(100)
                .rowMapper((rs, rowNumber) -> new SourceRow(
                        rs.getLong("id"), rs.getString("sku"), rs.getLong("price_cents")))
                .build();
    }
}
```

## 3. Processor와 Writer의 책임

`ItemProcessor`는 읽기 모델을 출력 모델로 매핑하고, 유효성 규칙과 제외 조건을 적용한다. 적재 대상이 아니면 `null`을 반환해 필터링하고, 잘못된 입력은 의도한 예외를 발생시켜 스킵 또는 실패 정책이 처리하게 한다. 롤백 뒤 같은 입력이 재처리될 수 있으므로 변환 결과는 재현할 수 있게 한다. [Spring Batch 5.2 · Item Processing](https://docs.spring.io/spring-batch/reference/5.2/processor.html)

`JdbcBatchItemWriter`는 명시적인 SQL과 바인딩으로 청크를 기록한다. `JpaItemWriter`는 트랜잭션의 `EntityManager`에서 엔티티를 병합하거나 설정에 따라 영속화한 뒤 플러시한다. Spring Batch 5.2에서는 Writer가 기본적으로 쓰기 후 영속성 컨텍스트를 비운다. 청크가 클 때 JDBC 배치 크기와 JPA 플러시·메모리 사용량을 함께 측정한다. [Spring Batch 5.2 · Database Writers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/database.html) · [JpaItemWriter API](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/database/JpaItemWriter.html)

## 4. Scheduler에서 Job 실행하기

`@EnableScheduling`을 활성화하고 `@Scheduled` 메서드가 처리할 기준일과 그날의 입력 버전을 정한 뒤 `JobLauncher.run(...)`을 호출하도록 한다. cron 시간대, 재실행, 휴일·누락일 정책을 업무 달력에 맞춘다. 예를 들어 서울 시간으로 전날 마감 데이터를 처리한다면 크론과 기준일 계산에 `Asia/Seoul`을 함께 사용한다. [Spring Framework · Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)

여러 인스턴스에서 스케줄러가 각각 실행될 수 있다. 공유 JobRepository로 동일 JobInstance의 실행을 조정하고, 스케줄 실행자를 하나로 제한해야 하면 외부 스케줄러나 별도 분산 조정을 사용한다. 실패 작업을 이어갈 때는 원래 식별 파라미터를 유지한다. 매 실행 시각을 새 식별 파라미터로 추가하면 동일 기준일에도 새 인스턴스가 시작된다.

관련 문서 [Spring Batch Item Readers and Checkpoints](06_spring_batch_item_readers_and_checkpoints.md) · [Spring Batch Item Writers and Output](07_spring_batch_item_writers_and_output.md)
