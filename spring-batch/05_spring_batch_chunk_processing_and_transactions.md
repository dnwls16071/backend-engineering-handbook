# Spring Batch Chunk Processing and Transactions

## 1. 여러 항목을 한 트랜잭션에서 처리하기

청크 Step은 `ItemReader`로 항목을 하나씩 읽고 선택적으로 `ItemProcessor`로 변환한다. `ItemWriter`는 청크의 출력 항목을 받아 한 번에 기록한다. 기본적인 청크 흐름에서는 정해 둔 개수만큼 읽거나 입력이 끝나면 쓰기를 수행하고 트랜잭션을 커밋한다. [Spring Batch 5.2 · Chunk-oriented Processing](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing.html)

```text
청크 트랜잭션 시작 → 항목 읽기와 변환 → 청크 쓰기 → 체크포인트 갱신과 커밋
```

청크 크기는 읽는 입력 항목을 기준으로 한다. 변환 중 일부가 필터링되면 Writer가 받는 항목 수는 줄어든다. 입력의 마지막 청크도 설정값보다 작을 수 있다. 쓰기에 실패해 트랜잭션이 롤백되면 해당 청크의 DB 변경은 되돌아가고, 이전에 커밋한 청크는 남는다. 재시도 설정에 따라 동일한 항목을 다시 처리할 수 있다. [Spring Batch 5.2 · Chunk Step Configuration](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/configuring.html) · [Spring Batch 5.2 · Controlling Rollback](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/controlling-rollback.html)

## 2. 카탈로그 CSV를 정규화해서 저장하기

다음 Step은 [CSV 리더](06_spring_batch_item_readers_and_checkpoints.md), [프로세서](08_spring_batch_item_processing_and_filtering.md), [JDBC Writer](07_spring_batch_item_writers_and_output.md)를 연결한다. 예제의 청크 크기 `100`은 입력 항목 수와 트랜잭션 비용을 측정하며 조정할 수 있다.

```java
import org.springframework.batch.core.Step;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemReader;
import org.springframework.batch.item.ItemWriter;
import org.springframework.transaction.PlatformTransactionManager;

public class CatalogChunk {

    public static Step step(JobRepository jobs, PlatformTransactionManager transactions,
                            ItemReader<CsvRow> reader, ItemProcessor<CsvRow, Entry> processor,
                            ItemWriter<Entry> writer) {
        return new StepBuilder("loadCatalog", jobs)
                .<CsvRow, Entry>chunk(100, transactions)
                .reader(reader)
                .processor(processor)
                .writer(writer)
                .build();
    }

    public record CsvRow(String sku, String name, long priceCents, boolean active) {
    }

    public record Entry(String sku, String name, long priceCents) {
    }
}
```

## 3. 재시작할 위치 기록하기

`ItemStream.open(...)`은 이전 컨텍스트를 읽고, `update(...)`는 프레임워크가 저장할 현재 위치를 기록한다. `close()`는 파일이나 커서를 정리한다. 재시작 가능한 읽기·쓰기에서는 입력을 다시 열 때 체크포인트와 같은 데이터를 볼 수 있어야 한다. 같은 트랜잭션에 참여하지 않는 외부 호출은 롤백 뒤에도 결과가 남을 수 있으므로 재실행 규칙을 정한다. [Spring Batch 5.2 · ItemStream](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/item-stream.html) · [Spring Batch 5.2 · Configuring a Step for Restart](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/restart.html)
