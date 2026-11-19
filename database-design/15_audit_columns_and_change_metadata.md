# Audit Columns and Change Metadata

현재 행에 생성자와 수정자, 변경 시각, 마지막 변경 사유를 남기면 담당자가 최근 상태를 빠르게 확인할 수 있다. 변경 전후 값, 당시 상태의 복원, 변경 시점별 감사가 필요할 때는 별도의 변경 기록을 설계한다.

## 1. 감사 열의 의미 정하기

| 항목 | 설계 기준 |
| --- | --- |
| `created_at`, `created_by` | 최초 생성 시각과 생성 작업을 수행한 사용자 또는 시스템 식별자를 보존한다. |
| `updated_at`, `updated_by` | 마지막으로 의미 있는 쓰기가 발생한 시각과 행위자를 기록한다. 생성 시점에 두 수정 열도 함께 채우면 최근 변경순으로 동일하게 정렬할 수 있다. |
| `change_type`, `change_reason` | 분류나 집계에 사용하는 유형 코드를 저장하고, 설명이 필요한 경우 사유를 추가한다. 생성과 수정에서 어떤 값을 필수로 둘지 정한다. |
| `request_id`, `source_system` | 여러 서비스나 배치가 같은 작업을 수행할 때 요청과 쓰기 경로를 대조할 수 있도록 필요한 범위에서 기록한다. |
| `client_ip` | 접속 위치가 감사 목적에 필요한 경우만 기록하고 보존 기간을 정한다. |

행위자는 서버가 확인한 사용자 식별자나 서비스 식별자로 기록한다. 정보가 여러 저장소에 흩어질 때는 어떤 ID로 대조하는지 정의한다. 입력이나 접속 위치처럼 개인정보가 될 수 있는 값을 수집할 때는 감사 목적상 필요한 항목의 범위를 먼저 확인한다.

## 2. 변경 시각과 행위자를 함께 기록하기

실습 환경은 MySQL 8.4(InnoDB)다. 빈 스키마의 한 세션에서 실행한다. 시각 열은 `TIMESTAMP(6)`으로 정의하고 세션 시간대를 UTC로 맞춘다. MySQL의 `ON UPDATE`는 같은 행의 다른 값이 실제로 바뀔 때 수정 시각을 갱신하지만, 업무 사용자나 변경 사유는 애플리케이션이 같은 문에서 기록해야 한다.

```sql
SET time_zone = '+00:00';

CREATE TABLE db15_catalog_item (
    item_id BIGINT PRIMARY KEY,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    created_by VARCHAR(80) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    updated_by VARCHAR(80) NOT NULL,
    change_type VARCHAR(30) NOT NULL,
    change_reason VARCHAR(250)
) ENGINE = InnoDB;

INSERT INTO db15_catalog_item (
    item_id, price, created_at, created_by, updated_at, updated_by, change_type
) VALUES (
    10, 12.00, '2025-01-01 08:00:00', 'catalog/import',
    '2025-01-01 08:00:00', 'catalog/import', 'CREATE'
);

UPDATE db15_catalog_item
SET price = 13.50,
    updated_by = 'catalog/admin-8',
    change_type = 'PRICE_UPDATE',
    change_reason = 'Supplier price revision'
WHERE item_id = 10 AND price <> 13.50;

SELECT item_id, price, created_by, updated_by, change_type,
       updated_at > created_at AS changed_after_creation
FROM db15_catalog_item
WHERE item_id = 10;
```

결과는 `10, 13.50, catalog/import, catalog/admin-8, PRICE_UPDATE, 1`이다. 현재 행에서는 생성자와 마지막 수정자를 읽을 수 있다. 동일 가격을 다시 입력한 경우 `WHERE`가 제외하므로 예제의 변경 정보를 덮어쓰지 않는다. 사건 발생 시각과 시스템이 기록한 시각의 의미가 다르면 열을 분리한다. [MySQL 시각 열 자동 갱신](https://dev.mysql.com/doc/refman/8.4/en/timestamp-initialization.html) · [TIMESTAMP와 세션 시간대](https://dev.mysql.com/doc/refman/8.4/en/datetime.html)

## 3. 감사 열과 전체 이력의 차이

이 행을 다시 수정하면 `updated_by`, `change_reason`, `price`의 기존 값은 덮어써진다. 변경 이력이 필요한 경우 어떤 주체가 어떤 레코드에 수행한 변경인지, 전후 값과 기록 시각을 별도 이력에 남긴다. 데이터 수정과 이력 저장이 함께 성공해야 한다면 동일 트랜잭션으로 묶고, 기록 수정 권한과 보존 정책은 현재 데이터와 별도로 관리한다. DB 트리거를 쓰는 경우 직접 SQL 변경도 포착할 수 있지만, 애플리케이션 사용자 식별자는 신뢰할 수 있는 경로로 전달해야 한다. [MySQL 트리거](https://dev.mysql.com/doc/refman/8.4/en/trigger-syntax.html) · [트랜잭션 제어](https://dev.mysql.com/doc/refman/8.4/en/commit.html)
