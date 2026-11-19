# Soft Delete and Data Lifecycle

소프트 삭제는 행을 보존한 채 기본 업무 조회에서 제외한다. 삭제된 시각과 복구 가능 기간이 필요한지, 같은 업무 키로 새 행을 만들 수 있는지, 어떤 조건에서 실제 행을 제거할지 함께 정한다.

## 1. 삭제와 업무 상태 구분하기

| 방식 | 적합한 경우 | 결정할 내용 |
| --- | --- | --- |
| `is_deleted` | 삭제 여부만 기록하면 되는 경우 | 언제 누가 삭제했는지 별도로 남길지 정한다. |
| `deleted_at` | 삭제 시각, 복구 기한, 정리 대상을 구분해야 하는 경우 | `NULL`을 활성 상태로 쓰고 시간대를 통일한다. |
| 업무 상태 | 주문의 접수, 취소, 환불처럼 단계별로 허용 동작이 다른 경우 | 상태 전이와 각 상태에서 보이는 목록을 정의한다. |
| 물리 삭제 또는 별도 이력 보관 | 활성 테이블을 줄이거나 정해진 시점에 제거해야 하는 경우 | 참조 데이터, 보존 기간, 백업과 이력의 삭제 범위를 별도로 관리한다. |

삭제 표시가 한 번 붙었다가 제거되면 `deleted_at`만으로는 과거의 삭제와 복구를 재현할 수 없다. 사건 자체를 남겨야 하면 삭제와 복구를 이력으로 추가한다. 부모의 삭제 표시가 자식에게 자동으로 전파되는지도 결정한다. 외래 키는 참조하는 행의 존재를 검사하며, 부모가 활성인지까지 검사하지 않는다. [MySQL 외래 키 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html) · [행 버전과 이력 테이블](16_row_versioning_and_history_tables.md)

## 2. 활성 행에만 업무 키의 유일성 적용하기

MySQL에서는 `UNIQUE` 키에 `NULL`이 여러 개 들어갈 수 있다. `(login_id, deleted_at)`에 고유 제약을 두면 삭제 시각이 `NULL`인 활성 행도 같은 로그인 ID를 여러 건 가질 수 있다. 활성 행에서만 `login_id`를 반환하는 생성 열에 고유 제약을 두면 삭제한 행은 보존하고 활성 키의 중복을 막을 수 있다. 일부 DBMS는 조건부 고유 인덱스로 같은 정책을 표현한다. [MySQL CREATE TABLE의 UNIQUE 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [MySQL 생성 열](https://dev.mysql.com/doc/refman/8.4/en/create-table-generated-columns.html) · [PostgreSQL Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)

실습 환경은 MySQL 8.4(InnoDB)다. 빈 스키마에서 기존 회원의 로그인 ID를 새 회원이 사용할 수 있게 한 뒤, 삭제 주문을 제외하면서 주문이 없는 회원도 조회한다.

```sql
CREATE TABLE dd17_members (
    member_id INT PRIMARY KEY,
    login_id VARCHAR(80) NOT NULL,
    deleted_at DATETIME(6),
    active_login_id VARCHAR(80) GENERATED ALWAYS AS (
        CASE WHEN deleted_at IS NULL THEN login_id END
    ) STORED,
    UNIQUE (active_login_id)
) ENGINE = InnoDB;

CREATE TABLE dd17_orders (
    order_id INT PRIMARY KEY,
    member_id INT NOT NULL,
    deleted_at DATETIME(6),
    FOREIGN KEY (member_id) REFERENCES dd17_members (member_id)
) ENGINE = InnoDB;

INSERT INTO dd17_members (member_id, login_id) VALUES
    (1, 'min'), (2, 'jo'), (3, 'ru');
INSERT INTO dd17_orders (order_id, member_id, deleted_at) VALUES
    (10, 1, NULL), (11, 2, '2026-11-01 00:00:00'), (12, 3, NULL);

UPDATE dd17_members
SET deleted_at = '2026-11-02 00:00:00'
WHERE member_id = 1 AND deleted_at IS NULL;

INSERT INTO dd17_members (member_id, login_id) VALUES (4, 'min');

SELECT member_id, login_id, deleted_at IS NULL AS is_active
FROM dd17_members
WHERE login_id = 'min'
ORDER BY member_id;

SELECT m.member_id, COUNT(o.order_id) AS active_orders
FROM dd17_members AS m
LEFT JOIN dd17_orders AS o
  ON o.member_id = m.member_id AND o.deleted_at IS NULL
WHERE m.deleted_at IS NULL
GROUP BY m.member_id
ORDER BY m.member_id;
```

첫 조회에서 `min`의 회원 ID 1은 비활성, ID 4는 활성이다. 두 번째 조회의 주문 수는 회원 2가 `0`, 3이 `1`, 4가 `0`이다. 자식의 삭제 조건을 `ON`에 두면 삭제된 자식만 있는 회원도 0건으로 남는다. 이 상태에서 회원 1의 `deleted_at`을 `NULL`로 복구하려 하면 활성 키가 이미 사용 중이므로 고유 제약이 변경을 거부한다. 복구와 신규 가입은 다른 동작으로 정의하고 기존 주문 연결은 원래 회원 ID에서 유지한다. [MySQL JOIN](https://dev.mysql.com/doc/refman/8.4/en/join.html) · [MySQL의 외부 조인 최적화](https://dev.mysql.com/doc/refman/8.4/en/outer-join-optimization.html)

## 3. 읽기 조건과 정리 작업을 함께 설계하기

기본 조회, 검색, 집계에 활성 조건을 동일하게 적용하고 관리·복구 조회는 별도로 둔다. 활성 행이 대부분이라면 `deleted_at` 단독 인덱스로 줄일 수 있는 범위는 작다. 회원별 주문 조회처럼 업무 조건이 먼저 좁혀지는 경우 `(member_id, deleted_at)`를 후보로 두고, 삭제 시각 범위로 정리하는 배치는 별도의 접근 경로로 검토한다. 실행 계획은 실제 활성·삭제 비율과 읽기 조건을 기준으로 비교한다. [복합 인덱스와 커버링 인덱스](../database/08_composite_and_covering_indexes.md) · [MySQL 복합 인덱스](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html)
