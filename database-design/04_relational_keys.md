# Relational Keys

논리적 모델링에서 키는 행의 정체성과 테이블 간 참조 규칙을 정의한다. 어떤 값이 업무상 중복되면 안 되는지 먼저 파악하고, 그중 어떤 값을 대표 식별자로 사용할지 결정한다.

## 1. 유일성과 최소성으로 후보 키 찾기

| 종류 | 판단 기준 |
| --- | --- |
| 슈퍼 키 | 값의 조합으로 행을 하나만 찾을 수 있다. 식별에 불필요한 열을 포함할 수 있다. |
| 후보 키 | 유일하면서 어느 열을 빼도 유일성을 잃는 최소 조합이다. |
| 기본 키 | 후보 키 중에서 테이블의 대표로 선택한 키다. 한 테이블에 하나를 선언하며 각 구성 열에 `NULL`을 허용하지 않는다. |
| 대체 키 | 기본 키로 선택하지 않은 후보 키다. 값이 반드시 존재하고 유일해야 한다면 `NOT NULL`과 `UNIQUE`로 규칙을 표현한다. |
| 외래 키 | 같은 테이블 또는 다른 테이블의 참조 대상과 연결한다. 일반적으로 대상의 기본 키나 유일성이 보장된 키를 참조한다. |

회원 ID와 로그인 이메일이 각각 유일하다면 두 값은 별개의 후보 키다. 이메일이 유일하다는 이유로 `(email, joined_at)`도 행을 식별할 수 있지만, 가입 시각을 빼도 되므로 최소성은 만족하지 않는다. MySQL 8.4에서 `UNIQUE`만 사용하면 `NULL`을 여럿 허용하므로, 필수인 후보 키에는 `NOT NULL`도 지정한다. [MySQL CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)

## 2. 자연 키와 대리 키 선택하기

자연 키는 회원 이메일이나 외부 발급 코드처럼 업무에서 이미 사용하는 값이다. 대리 키는 행을 식별하기 위해 생성한 값이다. 자연 키가 바뀌면 이를 참조하는 외래 키나 외부 시스템의 식별자까지 영향을 받을 수 있다. 오래 유지되는 짧은 업무 식별자는 자연 키로 쓰기 좋고, 값이 바뀔 수 있거나 여러 시스템이 함께 참조하면 대리 키와 업무 키의 유일성 제약을 함께 두는 구성이 적합하다.

대리 키를 사용하면 업무 값으로 검색하는 쿼리에는 별도의 유일 인덱스나 조인이 필요할 수 있다. 참조 키의 폭, 변경 빈도, 실제 조회를 함께 본다. MySQL InnoDB는 각 보조 인덱스 엔트리에 기본 키 열을 포함하므로 기본 키가 길수록 보조 인덱스의 저장 비용도 늘어난다. 대리 키의 크기와 삽입 특성은 정수 시퀀스나 UUID 등 생성 방식에 따라 달라진다. [MySQL InnoDB Clustered and Secondary Indexes](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)

## 3. 복합 키로 행의 단위 표현하기

복합 키는 둘 이상의 열을 묶은 키다. 예를 들어 주문 항목은 주문 번호와 주문 안에서 부여한 줄 번호의 조합으로 식별할 수 있다. 기본 키를 `(order_id, line_no)`로 두면 이 항목을 참조하는 외래 키도 두 열을 함께 사용한다. 다른 테이블이 항목을 자주 참조한다면 별도의 `item_id`를 기본 키로 두고 `UNIQUE (order_id, line_no)`로 업무 규칙을 표현할 수 있다.

연결 테이블에서 기본 키나 유일성 제약을 두 외래 키의 조합으로 두면 같은 쌍을 한 번만 기록한다. 재등록이나 이력처럼 같은 쌍이 여러 번 생길 수 있다면 회차, 시작 시각, 줄 번호 등 행을 구별하는 기준을 먼저 정한다. [MySQL CREATE TABLE](https://dev.mysql.com/doc/refman/8.4/en/create-table.html) · [MySQL FOREIGN KEY Constraints](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)

## 4. MySQL 8.4 실습 · 업무 값 변경과 참조 유지

실습 환경은 MySQL 8.4(InnoDB)다. 빈 스키마에서 회원의 이메일을 바꿔도 같은 회원 ID로 주문이 연결되는지 확인한다.

```sql
CREATE TABLE dd04_members (
    member_id BIGINT PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE dd04_orders (
    order_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL,
    FOREIGN KEY (member_id) REFERENCES dd04_members (member_id)
) ENGINE = InnoDB;

INSERT INTO dd04_members VALUES (1, 'first@example.com');
INSERT INTO dd04_orders VALUES (101, 1);

UPDATE dd04_members SET email = 'updated@example.com' WHERE member_id = 1;

SELECT o.order_id, m.member_id, m.email
FROM dd04_orders AS o
JOIN dd04_members AS m ON m.member_id = o.member_id;
```

조회 결과는 `101, 1, updated@example.com`이다. 다른 회원에게 같은 이메일을 부여하는 쓰기는 `UNIQUE` 때문에 실패한다. 이메일의 대소문자 비교처럼 업무상 같은 값의 기준은 데이터베이스의 비교 규칙에 맞춰 정의한다. [MySQL Collation of Expressions](https://dev.mysql.com/doc/refman/8.4/en/charset-collation-coercibility.html)
