# Spring Batch Database Readers, Writers, and Delegation

상품 테이블에서 데이터를 읽어 검색용 문서나 캐시를 갱신하는 작업을 예로 든다. Spring Batch 5.2에서 저장소별 Reader와 Writer를 고르고, 이미 구현한 조회·저장 메서드를 배치에 위임할 때 지켜야 할 계약을 살펴본다.

## 1. 관계형 데이터베이스 읽기와 쓰기

| 구성 | 적합한 경우 | 실행에서 확인할 내용 |
| --- | --- | --- |
| `JdbcCursorItemReader`·`JpaCursorItemReader` | 결과를 순서대로 스트리밍한다. | 연결과 커서의 수명, 실제 드라이버의 페치 동작을 확인한다. |
| `JdbcPagingItemReader`·`JpaPagingItemReader` | 정렬된 입력을 페이지 단위로 가져온다. | 유일하고 안정적인 정렬 키와 실행 중 변하지 않는 조회 범위를 사용한다. 같은 기준일로 재실행할 때 입력 버전도 유지한다. |
| `JdbcBatchItemWriter` | SQL과 바인딩을 직접 지정해 청크를 일괄 기록한다. | Step의 트랜잭션과 같은 데이터소스를 사용하고, 기존 업무 키와 충돌했을 때의 규칙을 정한다. |
| `JpaItemWriter` | 엔티티를 쓰고 청크 단위로 플러시한다. | 트랜잭션에 바인딩된 `EntityManager`를 사용한다. 플러시 시점, 메모리 사용량, Hibernate의 실제 JDBC 배치 설정을 함께 확인한다. |

청크 크기는 커밋 단위이고 페이지 크기는 조회 단위다. 예를 들어 `id`가 증가하는 입력에서 시작 시점의 최대 ID를 저장한 뒤 그 범위만 읽으면, 실행 도중 추가되는 데이터가 작업에 섞이는 것을 줄일 수 있다. 기존 행의 수정·삭제까지 격리해야 한다면 입력 스냅샷이나 변경 이력도 필요하다. [Spring Batch 5.2 · Database Readers and Writers](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/database.html) · [DB Paging Reader와 Scheduling](14_spring_batch_database_pipelines_and_scheduling.md)

## 2. MongoDB와 Redis는 재처리 기준이 다르다

| 저장소 | Reader | Writer와 복구 |
| --- | --- | --- |
| MongoDB | `MongoCursorItemReader` 또는 `MongoPagingItemReader`에 컬렉션, 필터, 정렬을 지정한다. 예를 들어 고정한 입력 버전을 `_id`로 정렬한다. | `MongoItemWriter`의 UPSERT는 문서의 `_id`로 기존 문서를 찾아 교체한다. 동일 상품을 재처리할 때 같은 `_id`를 사용하고, 원본에 없던 필드가 통째로 교체돼도 되는 문서인지 확인한다. |
| Redis | `RedisItemReader`는 `SCAN`으로 키를 찾고 키별 값을 읽는다. 스캔 도중 데이터가 바뀌거나 중복 키가 반환될 수 있다. | `RedisItemWriter`는 키를 추출해 값을 설정하거나 삭제한다. 캐시 재생성처럼 동일 키를 다시 써도 되는 작업에 맞고, 누락을 허용할 수 없는 원본 적재에는 안정적인 입력 목록을 사용한다. |

Spring Batch 5.2.2의 `RedisItemReader`는 열 때 새 스캔을 시작하며 커서 위치를 체크포인트에 저장하지 않는다. 또한 스캔에서 얻은 키가 만료되어 값을 읽지 못하면 `null`이 Step에서 입력 종료로 해석될 수 있다. 처리해야 할 키 집합이 중요하면 만료되는 캐시를 직접 순회하는 대신 원본의 고정 목록을 사용한다. [Spring Batch 5.2.2 · RedisItemReader](https://github.com/spring-projects/spring-batch/blob/v5.2.2/spring-batch-infrastructure/src/main/java/org/springframework/batch/item/redis/RedisItemReader.java) · [Redis · SCAN](https://redis.io/docs/latest/commands/scan/)

MongoDB Writer는 활성 트랜잭션이 있으면 쓰기를 커밋 직전까지 버퍼링할 수 있다. PostgreSQL에 저장하는 체크포인트와 MongoDB 또는 Redis에 쓰는 결과는 서로 다른 저장소에 있다. 재시도 시 동일 키로 다시 기록할 수 있게 하고, PostgreSQL 커밋 직전에 외부 쓰기가 반영된 뒤 실패하는 경우도 검증한다. [Spring Batch 5.2.2 · MongoItemWriter](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/data/MongoItemWriter.html) · [Spring Data MongoDB · Transactions](https://docs.spring.io/spring-data/mongodb/reference/mongodb/client-session-transactions.html)

## 3. 기존 메서드를 위임 Reader와 Writer에 연결하기

`ItemReaderAdapter`는 기존 메서드의 반환값을 다음 항목으로 사용한다. 메서드가 `null`을 반환하면 입력이 끝난다. 어댑터가 대상 메서드의 위치를 자동으로 저장하지 않으므로, 재시작이 필요하면 대상 상태를 별도 `ItemStream`으로 관리하거나 체크포인트를 지원하는 Reader를 사용한다. [Spring Batch 5.2 · Reader and Writer Implementations](https://docs.spring.io/spring-batch/reference/5.2/readers-and-writers/item-reader-writer-implementations.html)

`ItemWriterAdapter`는 청크를 받아 항목별로 대상 메서드를 호출한다. 아래 예제는 기존 JDBC 저장 메서드를 배치 Writer로 재사용한다. `catalog_projection` 테이블의 `sku`가 기본 키이고, `JdbcTemplate`이 Step의 트랜잭션에 참여하는 구성을 전제로 한다. 여러 행을 전송하는 비용이 병목이라면 청크 단위 `JdbcBatchItemWriter`를 검토한다. [Spring Batch 5.2.2 · ItemWriterAdapter](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/adapter/ItemWriterAdapter.html) · [PostgreSQL · INSERT](https://www.postgresql.org/docs/17/sql-insert.html)

```java
import org.springframework.batch.item.adapter.ItemWriterAdapter;
import org.springframework.jdbc.core.JdbcTemplate;

public class CatalogProjectionWriter {
    public record Row(String sku, String name, long priceCents) {}

    public static ItemWriterAdapter<Row> create(JdbcTemplate jdbc) throws Exception {
        var writer = new ItemWriterAdapter<Row>();
        writer.setTargetObject(new CatalogUpdates(jdbc));
        writer.setTargetMethod("upsert");
        writer.afterPropertiesSet();
        return writer;
    }

    public static class CatalogUpdates {
        private final JdbcTemplate jdbc;

        public CatalogUpdates(JdbcTemplate jdbc) {
            this.jdbc = jdbc;
        }

        public void upsert(Row row) {
            jdbc.update("""
                    INSERT INTO catalog_projection (sku, name, price_cents)
                    VALUES (?, ?, ?)
                    ON CONFLICT (sku) DO UPDATE
                    SET name = EXCLUDED.name, price_cents = EXCLUDED.price_cents
                    """, row.sku(), row.name(), row.priceCents());
        }
    }
}
```

직접 연결한 `ItemStream`은 Step에 자동 등록된다. 커스텀 위임 객체가 수명주기를 전달하지 않으면 내부 Stream을 `.stream(...)`으로 등록한다. `CompositeItemWriter`는 기본적으로 Stream 콜백을 전달하므로 같은 대상을 중복 등록할 필요가 없다. 여러 대상에 쓸 때는 각 대상이 같은 트랜잭션 자원에 참여하는지도 확인한다. [Spring Batch 5.2 · Registering ItemStream](https://docs.spring.io/spring-batch/reference/5.2/step/chunk-oriented-processing/registering-item-streams.html) · [Spring Batch 5.2.2 · CompositeItemWriter](https://docs.spring.io/spring-batch/docs/5.2.2/api/org/springframework/batch/item/support/CompositeItemWriter.html)

## 4. Docker의 PostgreSQL에서 동기화 검증하기

[13번 Docker 환경](13_spring_batch_execution_metadata_and_transaction_boundaries.md#3-docker의-postgresql에서-실행-기록-읽기)에서 고정한 원본 행을 두 건씩 처리한다. 마지막 청크에 일부러 오류를 내 앞서 커밋한 상품만 남는지 확인한다. 같은 입력으로 재시작해 누락 없이 끝났는지 확인하고, 새 인스턴스에서 같은 SKU에 수정한 이름과 가격을 넣어 기존 행이 갱신되는지 확인한다.

Spring Batch 5.2.2와 PostgreSQL 17에서 두 번째 청크를 쓴 직후 오류를 발생시켰다. 위임 Writer가 실행한 두 번째 청크의 SQL은 롤백됐고, 재시작 후 고유 SKU 네 건이 남았다. 입력 버전을 올려 다시 실행하자 행 수는 네 건으로 유지되면서 기존 SKU의 가격이 갱신됐다.

관련 문서 [Spring Batch Parallelism and Transaction Boundaries](16_spring_batch_parallelism_and_transaction_boundaries.md) · [Processing CSV and JSON Files with Spring Batch](19_processing_csv_and_json_files_with_spring_batch.md)
