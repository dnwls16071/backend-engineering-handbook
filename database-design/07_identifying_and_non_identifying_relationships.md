# Identifying and Non-Identifying Relationships

식별 관계와 비식별 관계는 **부모의 키가 자식의 기본 키에 참여하는지**로 구분한다. 자식이 부모에 반드시 연결되어야 하는지, 부모를 지울 때 자식을 어떻게 처리할지는 각각 참여도와 삭제 정책에서 결정한다.

## 일대다에서 자식의 식별 기준 정하기

주문의 항목 번호 `line_no`는 주문 안에서만 유일하다고 가정한다. 주문 항목을 식별하는 방법은 두 가지다.

| 구분 | 주문 항목의 기본 키 | 주문과 연결하는 외래 키 | 주문별 항목 번호 중복 방지 |
| --- | --- | --- | --- |
| 식별 관계 | `(order_id, line_no)` | `order_id` | 복합 기본 키가 보장 |
| 비식별 관계 | `order_item_id` | `order_id` | `UNIQUE (order_id, line_no)`로 보장 |

식별 관계에서는 `(주문 42, 항목 2)`로 행을 식별한다. 비식별 관계에서는 `order_item_id`로 행을 식별하고, 주문별 번호는 별도의 업무 제약으로 유지한다. 두 설계 모두 `order_id`의 필수 참여를 보장할 수 있다. 식별 관계에서는 기본 키의 구성 열이므로 필수이고, 비식별 관계에서는 `NOT NULL`을 선언한다. [Oracle Data Modeler의 관계와 식별자](https://docs.oracle.com/en/database/oracle/sql-developer-data-modeler/24.3/dmdug/data-modeler-concepts-usage.html) · [PostgreSQL의 기본 키와 외래 키 제약](https://www.postgresql.org/docs/current/ddl-constraints.html)

## 일대일에서 공유 키와 독립 키 비교하기

회원 상세 정보가 회원당 최대 한 건이라면, 자식의 `member_id`를 기본 키이자 외래 키로 두는 공유 기본 키가 식별 관계의 예다. 상세 정보에 자체 `member_detail_id`를 두고, `member_id`에 `NOT NULL`과 `UNIQUE`를 적용하면 비식별 관계로 같은 개수 제한을 표현할 수 있다.

두 방법 모두 상세 정보가 없는 회원을 허용한다. 상세 정보가 여러 건으로 바뀌면 독립 키 설계에서는 상세 행의 식별자를 유지한 채 `UNIQUE` 범위를 재설계할 수 있다. 공유 키 설계에서는 새 기본 키와 기존 참조를 함께 검토해야 한다.

## 다대다 연결 테이블에 업무 규칙 남기기

학생이 한 강좌에 한 번만 등록할 수 있을 때는 연결 테이블의 기본 키로 `(student_id, course_id)`를 쓰면 두 부모에 대한 식별 관계가 된다. 등록 자체에 외부 참조가 많거나 같은 학생의 재등록 이력을 다루려면 독립적인 `enrollment_id`를 기본 키로 둘 수 있다. 이 경우 중복 기준을 `(student_id, course_id, term_id)`처럼 실제 규칙에 맞는 유일성 제약으로 표현한다.

기본 키를 독립적으로 정하더라도 자연 키나 연결 조합의 유일성은 따로 확인한다. 업무 식별자가 고정되어 있고 연결 자체의 식별 기준과 일치한다면 복합 기본 키도 직접적인 표현이다. [기본 키와 유일성 제약](https://www.postgresql.org/docs/current/ddl-constraints.html) · [앞선 다대다 모델](06_one_to_one_and_many_to_many_relationships.md)

## 변경 비용과 조회 경로 비교하기

- 복합 키를 여러 후속 테이블이 참조하면 외래 키 열과 조인 조건도 함께 늘어날 수 있다. 외부 API나 이력 레코드가 해당 행을 자주 참조한다면 식별자를 안정적으로 유지할 수 있는지 확인한다.
- `(order_id, line_no)` 순서의 B-tree 인덱스는 `order_id`로 주문의 항목들을 찾는 데 사용할 수 있다. 독립 키 설계에서도 같은 열 조합에 유일성 인덱스를 두면 이 조회 경로를 제공할 수 있다.
- 보조 인덱스에 기본 키를 함께 저장하는 구현에서는 기본 키의 폭이 저장 비용에 영향을 줄 수 있다. MySQL의 InnoDB가 여기에 해당한다. 실제 조회와 쓰기 비용은 사용하는 DBMS, 데이터 분포, 함께 필요한 인덱스를 기준으로 비교한다. [MySQL 복합 인덱스](https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html) · [InnoDB 기본 인덱스와 보조 인덱스](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)
