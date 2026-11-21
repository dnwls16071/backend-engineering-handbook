# PostgreSQL Upserts and MERGE

외부 카탈로그에서 같은 상품 키가 반복해서 들어올 수 있다. PostgreSQL 18에서 키 하나를 안전하게 삽입하거나 갱신할 때는 `INSERT ... ON CONFLICT`를 쓰고, 소스와 대상의 매칭 결과에 따라 삽입·갱신·삭제를 섞을 때는 `MERGE`를 쓴다. [PostgreSQL 18 · INSERT](https://www.postgresql.org/docs/18/sql-insert.html) · [PostgreSQL 18 · MERGE](https://www.postgresql.org/docs/18/sql-merge.html)

## 1. 유일 키에 대한 업서트

`ON CONFLICT (sku)`는 `sku`에 해당하는 유일 인덱스를 찾는다. 이 예에서는 기본 키의 인덱스가 쓰인다. `DO UPDATE`에는 충돌 대상을 명시해야 하며, `ON CONSTRAINT`로 제약 이름을 지정할 수도 있다. 즉시 검사되는 유일 제약이나 유일 인덱스가 충돌을 판정한다. [PostgreSQL 18 · ON CONFLICT Clause](https://www.postgresql.org/docs/18/sql-insert.html#SQL-ON-CONFLICT)

```sql
CREATE TABLE catalog_price (
    sku text PRIMARY KEY,
    unit_price numeric(12, 2) NOT NULL CHECK (unit_price >= 0),
    feed_version bigint NOT NULL
);

INSERT INTO catalog_price AS p (sku, unit_price, feed_version)
VALUES ('LAMP-01', 24900, 12)
ON CONFLICT (sku) DO UPDATE
SET unit_price = EXCLUDED.unit_price,
    feed_version = EXCLUDED.feed_version
WHERE p.feed_version < EXCLUDED.feed_version
RETURNING sku, unit_price, feed_version;
```

`p`는 기존 행, `EXCLUDED`는 삽입하려던 행을 가리킨다. 같은 키가 들어오면 서버가 충돌을 판정하고, 조건 없는 `DO UPDATE`는 별도 오류가 없는 한 동시 쓰기에서도 삽입이나 갱신 중 하나를 원자적으로 수행한다. 이 예에서는 더 높은 버전만 갱신하므로 같은 버전이나 오래된 버전을 보내면 충돌한 행을 잠그고 갱신을 건너뛴다. `RETURNING`도 그 경우에는 0행을 반환한다. 기존 값을 항상 보존하려면 `DO NOTHING`을 사용한다. [PostgreSQL 18 · INSERT](https://www.postgresql.org/docs/18/sql-insert.html) · [PostgreSQL 18 · Read Committed](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

한 `INSERT ... ON CONFLICT DO UPDATE` 문에서 동일한 키가 여러 번 나오면 같은 대상 행을 두 번 처리할 수 없어 카디널리티 오류가 발생한다. 일괄 적재에서는 키마다 최신 버전과 입력 순서 같은 기준으로 한 행을 먼저 고른다. [PostgreSQL 18 · ON CONFLICT Clause](https://www.postgresql.org/docs/18/sql-insert.html#SQL-ON-CONFLICT)

## 2. 배치 입력을 `MERGE`로 반영하기

아래 입력은 삭제 이벤트와 가격 변경 이벤트를 함께 전달한다. `DISTINCT ON`은 `sku`마다 가장 높은 버전을 남기고 버전이 같으면 더 큰 `event_id`를 고른다. `ON`은 상품 식별에 쓰고, 버전과 삭제 여부는 `WHEN`에 둔다. 각 후보 행에서 조건을 만족하는 첫 번째 분기만 실행된다. [PostgreSQL 18 · MERGE](https://www.postgresql.org/docs/18/sql-merge.html) · [PostgreSQL 18 · SELECT](https://www.postgresql.org/docs/18/sql-select.html)

```sql
MERGE INTO catalog_price AS p
USING (
    SELECT DISTINCT ON (sku) sku, unit_price, feed_version, retired
    FROM (VALUES
        ('LAMP-01', 23900, 11, false, 1),
        ('LAMP-01', 26900, 13, false, 2),
        ('LAMP-02', 33900,  1, false, 3)
    ) AS feed(sku, unit_price, feed_version, retired, event_id)
    ORDER BY sku, feed_version DESC, event_id DESC
) AS s
ON p.sku = s.sku
WHEN MATCHED AND s.retired AND s.feed_version > p.feed_version THEN
    DELETE
WHEN MATCHED AND NOT s.retired AND s.feed_version > p.feed_version THEN
    UPDATE SET unit_price = s.unit_price, feed_version = s.feed_version
WHEN NOT MATCHED BY TARGET AND NOT s.retired THEN
    INSERT (sku, unit_price, feed_version)
    VALUES (s.sku, s.unit_price, s.feed_version)
RETURNING merge_action() AS action, s.sku;
```

예제를 순서대로 실행하면 `LAMP-01`은 `UPDATE`, `LAMP-02`는 `INSERT`다. 이후 `LAMP-01`에 버전 14의 삭제 이벤트를 보내면 `DELETE`가 실행된다. 삭제 뒤 오래된 이벤트가 재전송될 수 있는 시스템에서는 삭제 버전도 별도로 보존해야 재삽입을 막을 수 있다. [PostgreSQL 18 · MERGE](https://www.postgresql.org/docs/18/sql-merge.html)

`READ COMMITTED`에서 `MERGE`가 미매칭 키를 삽입하려는 동안 다른 트랜잭션이 같은 키를 먼저 커밋하면 유일성 위반(`23505`)이 날 수 있다. 충돌 시 기존 행을 갱신하는 쓰기 경로에는 `ON CONFLICT DO UPDATE`의 동시성 동작이 적합하다. [PostgreSQL 18 · Read Committed](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED) · [PostgreSQL 18 · 오류 코드](https://www.postgresql.org/docs/18/errcodes-appendix.html)
