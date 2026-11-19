# Database Design Review and Next Steps

설계는 업무 용어와 규칙을 개념 모델에 표현하고, 논리 모델에서 키와 관계를 정한 뒤, 물리 모델로 옮겨 실제 저장과 조회를 검증하는 과정이다. 주문 모델을 다시 보면서 각 결정이 어디에 기록되는지 확인한다.

## 1. 설계 결정 다시 확인하기

| 검토할 질문 | 관련 문서 |
| --- | --- |
| 어떤 업무 요구를 해결하고, 각 단계에서 어떤 판단을 남기는가? | [설계 기초](01_database_design_fundamentals.md) |
| 주문과 상품은 어떤 사실을 담고, 한쪽에서 다른 쪽을 몇 건까지 참조하는가? | [개념적 모델링](02_conceptual_data_modeling.md) · [개념 모델링 실습](03_conceptual_modeling_workshop.md) |
| 행을 어떤 키로 식별하고, 참여의 필수 여부와 최대 개수를 어떻게 제약하는가? | [관계형 키](04_relational_keys.md) · [참여도와 일대다](05_relationship_participation_and_one_to_many.md) · [일대일과 다대다](06_one_to_one_and_many_to_many_relationships.md) |
| 부모 키가 자식의 식별에 포함되는가? 주문 항목의 고유 규칙은 어느 키에 담는가? | [식별·비식별 관계](07_identifying_and_non_identifying_relationships.md) · [논리 모델링 실습](08_logical_modeling_workshop.md) |
| 각 속성은 어느 키에 의해 결정되고, 한 사실의 수정이 다른 행에 어떤 영향을 주는가? | [정규화](09_database_normalization.md) |
| 자료형, 인덱스, 보존할 값은 무엇이며 어떤 쿼리로 검증하는가? | [물리적 모델링](10_physical_database_modeling.md) · [물리 모델링 실습](11_physical_modeling_workshop.md) |

예를 들어 주문당 성공 결제 최대 1건은 먼저 업무 규칙으로 선택한다. 논리 모델은 결제의 주문 참조에 고유 제약을 두고, 물리 모델은 실제 DBMS의 외래 키와 고유 제약으로 구현한다. 여러 차례의 결제를 기록해야 한다는 요구가 생기면, 성공한 결제의 정의와 부분 결제를 허용할지부터 다시 정한다. [Oracle Data Modeler의 설계 단계](https://docs.oracle.com/en/database/oracle/sql-developer-data-modeler/22.2/dmdug/data-modeler-concepts-usage.html) · [MySQL 외래 키 제약](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)

## 2. 다음 설계 주제로 이어가기

| 주제 | 모델링을 시작할 질문 |
| --- | --- |
| 상태 코드와 기준 정보 | 값의 목록과 사용 가능 기간을 누가 관리하는가? 이미 저장된 코드의 의미를 바꿀 수 있는가? |
| 변경 이력 | 어떤 사실의 과거 상태를 다시 조회해야 하는가? 업무상 효력이 발생한 시간과 변경이 기록된 시간을 구분해야 하는가? |
| 카테고리 계층 | 한 항목의 직접 부모는 하나인가? 하위 전체 검색과 부모 이동 중 어느 작업이 자주 발생하는가? |
| 복합 업무 규칙 | 취소, 부분 결제, 분할 배송처럼 예외가 생기면 기존 관계와 트랜잭션의 경계가 어떻게 바뀌는가? |

새 요구를 검토할 때는 한 행이 뜻하는 사실, 중복의 범위, 변경의 소유자를 먼저 합의한다. 그다음 정상 사례와 경계 사례로 제약 조건과 조회를 함께 확인한다. 필요하면 기본편의 [데이터 무결성](../database/09_data_integrity_and_constraints.md)과 [트랜잭션](../database/10_transactions_and_isolation_levels.md)으로 돌아간다.

설계 2부에서는 [공통 코드 설계](13_reference_data_and_code_tables.md)부터 계층, 이력, 가변 속성을 다룬다. 전체 주제는 [설계 패턴 복습](22_database_design_patterns_review_and_next_steps.md)에서 찾아갈 수 있다.
