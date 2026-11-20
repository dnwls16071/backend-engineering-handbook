# Processing CSV and JSON Files with Spring Batch

카탈로그 파일을 읽어 검증하고 다른 형식으로 내보내는 작업을 Spring Batch 5.2 기준으로 정리한다. CSV와 JSON은 같은 상품 레코드로 매핑하므로, 포맷별 Reader와 Writer를 바꿔도 업무 검증 규칙을 재사용할 수 있다.

## 1. 입력과 출력의 형식을 먼저 정한다

| 형식 | 읽기 | 쓰기 |
| --- | --- | --- |
| CSV 또는 고정폭 텍스트 | `FlatFileItemReader`가 줄을 읽고 토크나이저와 `FieldSetMapper`로 매핑한다. CSV는 구분자 기반, 고정폭 파일은 열 범위 기반 토크나이저를 쓴다. | `FlatFileItemWriter`가 `LineAggregator`로 항목을 한 줄씩 변환하고, 필요한 경우 헤더를 추가한다. |
| JSON 배열 | `JsonItemReader`와 `JacksonJsonObjectReader`가 최상위 배열의 객체를 한 항목씩 역직렬화한다. | `JsonFileItemWriter`와 `JacksonJsonObjectMarshaller`가 항목을 배열의 객체로 기록한다. |

예제 CSV는 UTF-8, `sku,name,priceCents` 헤더, 레코드당 한 줄을 사용한다. 이름 안의 쉼표나 큰따옴표는 인용 규칙에 따라 처리한다. 필드 내부 줄바꿈이 허용되는 파일은 `RecordSeparatorPolicy`를 입력 규칙에 맞춰 설정한다. JSON은 최상위 배열을 전제로 하며, 한 줄에 객체 하나가 오는 NDJSON은 별도 줄 기반 Reader로 구성한다. [Spring Batch 5.2 · FlatFileItemReader](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/flat-files/file-item-reader.html) · [FlatFileItemWriter](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/flat-files/file-item-writer.html) · [JSON Readers and Writers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/json-reading-writing.html)

## 2. 파일별 Reader와 Writer 구성

입력 파일과 출력 파일에 서로 다른 `FileSystemResource`를 사용한다. 아래 CSV Writer는 문자열을 인용하고 값에 들어 있는 큰따옴표를 두 번 쓴다. 입력이나 출력 경로를 Job 파라미터로 받을 때는 [Step 스코프](18_designing_spring_batch_steps_parameters_and_listeners.md#2-실행-파라미터와-scope를-연결하기)에서 자원을 생성한다.

```java
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.batch.item.file.FlatFileItemReader;
import org.springframework.batch.item.file.FlatFileItemWriter;
import org.springframework.batch.item.file.builder.FlatFileItemReaderBuilder;
import org.springframework.batch.item.file.builder.FlatFileItemWriterBuilder;
import org.springframework.batch.item.json.JacksonJsonObjectMarshaller;
import org.springframework.batch.item.json.JacksonJsonObjectReader;
import org.springframework.batch.item.json.JsonFileItemWriter;
import org.springframework.batch.item.json.JsonItemReader;
import org.springframework.batch.item.json.builder.JsonFileItemWriterBuilder;
import org.springframework.batch.item.json.builder.JsonItemReaderBuilder;
import org.springframework.core.io.Resource;
import org.springframework.core.io.WritableResource;

public class CatalogFileItems {
    public record Row(String sku, String name, long priceCents) {}

    public static FlatFileItemReader<Row> csvReader(Resource input) {
        return new FlatFileItemReaderBuilder<Row>()
                .name("catalogCsvReader").resource(input).encoding("UTF-8")
                .linesToSkip(1).delimited().names("sku", "name", "priceCents")
                .fieldSetMapper(fields -> new Row(fields.readString("sku"),
                        fields.readString("name"), fields.readLong("priceCents")))
                .build();
    }

    public static FlatFileItemWriter<Row> csvWriter(WritableResource output) {
        return new FlatFileItemWriterBuilder<Row>()
                .name("catalogCsvWriter").resource(output).encoding("UTF-8")
                .headerCallback(writer -> writer.write("sku,name,priceCents"))
                .lineAggregator(row -> csvField(row.sku()) + ","
                        + csvField(row.name()) + "," + row.priceCents())
                .build();
    }

    public static JsonItemReader<Row> jsonReader(Resource input) {
        var mapper = new ObjectMapper()
                .enable(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES)
                .enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);
        return new JsonItemReaderBuilder<Row>()
                .name("catalogJsonReader").resource(input)
                .jsonObjectReader(new JacksonJsonObjectReader<>(mapper, Row.class))
                .build();
    }

    public static JsonFileItemWriter<Row> jsonWriter(WritableResource output) {
        return new JsonFileItemWriterBuilder<Row>()
                .name("catalogJsonWriter").resource(output).encoding("UTF-8")
                .jsonObjectMarshaller(new JacksonJsonObjectMarshaller<>())
                .build();
    }

    private static String csvField(String value) {
        if (value.contains("\n") || value.contains("\r")) {
            throw new IllegalArgumentException("CSV fields must fit on one line");
        }
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }
}
```

업무 규칙은 Processor에서 검증한다. 예를 들어 빈 SKU와 음수 가격을 거절하고, 제외 가능한 레코드와 파일 전체를 중단할 형식 오류의 정책을 나눈다. `linesToSkip(1)`은 첫 줄을 건너뛰는 설정이므로 계약이 엄격할 때는 헤더 이름과 순서도 별도로 검사한다. [Spring Batch 5.2 · Item Processing](https://docs.spring.io/spring-batch/reference/5.2/processor.html) · [Skip Logic](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/configuring-skip.html)

## 3. 실패 후 파일을 이어 쓰고 완성본을 공개한다

1. [Docker Compose의 PostgreSQL](13_spring_batch_execution_metadata_and_transaction_boundaries.md#3-docker의-postgresql에서-실행-기록-읽기)을 JobRepository에 연결한다. 작업마다 원본 파일 버전과 출력 임시 경로를 고정한다.
2. 청크 길이를 2로 지정하고 세 번째 레코드에서 일부러 실패시킨다. 같은 식별 파라미터와 원본·출력 경로로 재시작해 Reader와 Writer가 마지막 커밋 위치부터 이어가는지 확인한다. 재시작 동안 임시 파일을 삭제하거나 수동으로 덧붙이지 않는다.
3. Job이 성공하면 CSV 헤더와 행 수, JSON 배열 파싱과 항목 수를 확인하고 임시 파일을 최종 경로로 옮긴다. 같은 파일시스템에서 원자적 이름 변경을 지원한다면 소비자가 반만 작성된 파일을 읽지 않도록 활용할 수 있다.

파일 Writer의 재시작에는 메타데이터와 임시 파일이 모두 필요하다. 재시작과 별개의 새 JobInstance가 기존 출력 경로를 사용할 때는 덮어쓰기, 새 출력 생성, 실행 거절 중 어떤 동작을 할지 정한다. JSON 배열은 Writer가 닫히면서 닫는 대괄호를 기록하므로, 쓰는 중인 파일은 공개 대상에서 제외한다. [Spring Batch 5.2 · ItemStream](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/item-stream.html) · [FlatFileItemWriter](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/flat-files/file-item-writer.html) · [JSON Readers and Writers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/json-reading-writing.html)

Spring Batch 5.2.2와 Docker의 PostgreSQL로 검증했다. 실패한 실행의 임시 파일도 두 건짜리 유효한 JSON 배열이었다. 재시작하자 네 건이 중복 없이 기록됐고, CSV로 되돌렸을 때 쉼표와 큰따옴표가 든 이름도 유지됐다. 파일을 파싱할 수 있다는 사실만으로 작업 완료를 판단할 수 없는 예다.

관련 문서 [Spring Batch Item Readers and Checkpoints](06_spring_batch_item_readers_and_checkpoints.md) · [Spring Batch Item Writers and Output](07_spring_batch_item_writers_and_output.md)
