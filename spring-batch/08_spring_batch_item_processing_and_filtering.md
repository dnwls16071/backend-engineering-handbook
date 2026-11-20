# Spring Batch Item Processing and Filtering

## 1. 입력을 출력 모델로 변환하기

`ItemProcessor<I, O>`는 읽은 항목 하나를 검증하거나 출력 모델로 변환한다. 비활성 상품처럼 정상 입력이지만 저장할 필요가 없는 항목에는 `null`을 반환한다. 필수 값이 비었거나 가격이 음수인 행은 예외로 분류하고, [스킵 정책](09_spring_batch_repeat_retry_and_skip.md)에 따라 처리한다. 필터링 건수와 스킵 건수는 별도로 기록된다. [Spring Batch 5.2 · Item Processing](https://docs.spring.io/spring-batch/reference/5.2/processor.html)

```java
import org.springframework.batch.item.ItemProcessor;

public class CatalogProcessor implements ItemProcessor<CatalogChunk.CsvRow, CatalogChunk.Entry> {

    @Override
    public CatalogChunk.Entry process(CatalogChunk.CsvRow row) {
        if (!row.active()) {
            return null;
        }

        String sku = row.sku().strip();
        String name = row.name().strip();
        if (sku.isEmpty() || sku.length() > 64 || name.isEmpty() || name.length() > 200
                || row.priceCents() < 0) {
            throw new InvalidCatalogRowException();
        }

        return new CatalogChunk.Entry(sku, name, row.priceCents());
    }

    public static class InvalidCatalogRowException extends RuntimeException {
        public InvalidCatalogRowException() {
            super("Invalid catalog row");
        }
    }
}
```

## 2. 처리 단계를 조합하고 반복에 대비하기

`CompositeItemProcessor`는 한 프로세서의 결과를 다음 프로세서로 전달한다. 검증, 정규화, 출력 변환을 같은 순서로 적용할 때 쓸 수 있다. `ClassifierCompositeItemProcessor`는 입력의 종류에 맞는 프로세서 하나를 선택한다. [Spring Batch 5.2 · Chaining ItemProcessors](https://docs.spring.io/spring-batch/reference/5.2/processor.html) · [Spring Batch 5.2 · Implementations](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/item-reader-writer-implementations.html)

청크가 롤백되면 같은 항목이 처리기에 다시 들어올 수 있다. 위 예제는 입력 객체를 그대로 두고 새 결과를 만들어 다시 실행해도 같은 변환 결과를 얻는다. 프로세서에 외부 변경을 넣는다면 반복 실행의 영향과 트랜잭션 참여 여부를 함께 검증한다. [Spring Batch 5.2 · Fault-Tolerant Item Processing](https://docs.spring.io/spring-batch/reference/5.2/processor.html)

5.2.2 실행 예제에서 쓰기 재시도와 스킵을 함께 발생시켰을 때, 비활성 행 하나가 다시 처리돼 `filterCount`가 2로 기록됐다. 필터링된 고유 상품 수가 필요하면 상품 키를 기준으로 집계한다. [Spring Batch 5.2 · Retry Logic](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/retry-logic.html)
