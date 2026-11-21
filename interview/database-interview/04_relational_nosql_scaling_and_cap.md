# Relational Databases, NoSQL, Scaling, and CAP

## 28. RDBMS와 NoSQL은 어떻게 다르고, 언제 각각 사용하나요?

**30–60초 답변**

> RDBMS는 데이터를 관계로 모델링하고 SQL로 조회하며, 키와 제약 조건으로 여러 테이블의 데이터 관계를 관리할 수 있습니다. NoSQL은 문서, 키-값, 그래프 등 여러 데이터 모델을 아우르므로 쿼리와 트랜잭션 보장은 제품마다 확인해야 합니다. 예를 들어 주문·결제·정산 데이터에 참조 무결성이 필요하고 조회 조합이 계속 늘어난다면 관계형 DB를 먼저 검토합니다. 상품 카탈로그에서 항목마다 속성이 다르고 개별 상품 문서 전체를 주로 읽는다면 문서 DB도 후보가 됩니다. 데이터 모델을 고른 뒤 실제 읽기와 쓰기 패턴, 제약 조건, 장애 시 허용 범위를 검증합니다. [PostgreSQL의 데이터 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html) · [MongoDB 데이터 모델링](https://www.mongodb.com/docs/manual/data-modeling/)

**꼬리 질문 · NoSQL에도 여러 레코드를 묶는 트랜잭션이 있나요?**

예를 들어 MongoDB는 복제 세트와 샤딩 클러스터에서 여러 문서를 묶는 트랜잭션을 지원합니다. 지원 여부와 비용은 제품, 저장 구조, 배포 방식에 따라 달라집니다. 함께 읽고 수정하는 데이터가 자연스럽게 한 문서에 속한다면, 한 문서의 원자적 연산으로 처리 범위를 줄일 수 있습니다. [MongoDB 트랜잭션](https://www.mongodb.com/docs/manual/core/transactions/)

## 29. 데이터 모델링 관점에서 RDBMS와 NoSQL의 설계 방식은 어떻게 다른가요?

**30–60초 답변**

> 관계형으로 설계할 때는 주문, 고객, 주문 항목 같은 엔터티와 관계, 지켜야 할 데이터 규칙을 먼저 식별합니다. 변경이 여러 행에 반복되지 않도록 정규화하고, 필요한 조회는 조인으로 구성할 수 있습니다. 문서 DB에서는 어떤 데이터를 함께 읽고 수정하는지 보고, 주문의 항목처럼 주문과 함께 다루는 데이터를 하나의 문서에 포함할 수 있습니다. DynamoDB 같은 키 기반 시스템에서는 조회 경로와 쓰기 분산을 고려해 파티션 키와 정렬 키를 정합니다. 조회를 위해 값을 중복 저장한다면 각 복사본을 언제 갱신하고 실패를 어떻게 복구할지 결정합니다. [PostgreSQL의 외래 키와 제약 조건](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK) · [MongoDB 문서 임베딩](https://www.mongodb.com/docs/manual/data-modeling/embedding/) · [DynamoDB 모델링 기초](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/data-modeling-foundations.html)

**꼬리 질문 · 주문에 상품 이름을 복사하면 데이터 중복 문제 아닌가요?**

주문 시점의 상품명과 단가를 계약 이력으로 남기는 경우에는 주문에 그 값을 저장하는 것이 맞습니다. 항상 최신 이름을 보여 줘야 하는 화면이라면 상품 ID로 조회하거나, 중복 사본을 언제까지 최신 상태로 맞출지 정책을 정합니다. 값이 같은 이유와 변경의 의미를 먼저 확인하면 스냅샷 보존과 최신 값 전파 중 무엇이 필요한지 구분할 수 있습니다. [MongoDB의 데이터 일관성 모델링](https://www.mongodb.com/docs/manual/data-modeling/data-consistency/)

## 30. 관계형 DB에서도 스케일 아웃이 가능한가요?

**30–60초 답변**

> 조회 부하는 복제본으로 분산할 수 있습니다. 비동기 복제본에는 반영 지연이 있으므로 방금 저장한 값을 바로 보여 줘야 하는 요청은 기본 서버로 보내는 등의 읽기 정책이 필요합니다. 단일 DB의 쓰기 용량이 한계라면 고객 ID 같은 샤드 키로 데이터를 여러 서버에 분할해 서로 다른 샤드가 쓰기를 나눠 처리할 수 있습니다. 그 경우 요청을 올바른 샤드로 보내야 하고, 샤드를 가로지르는 조인이나 트랜잭션은 조율 비용이 늘어납니다. 예를 들어 Vitess는 MySQL 샤딩을 제공하며, 주요 트랜잭션이 한 샤드에서 끝나도록 키를 설계할 수 있습니다. [PostgreSQL 읽기 복제본과 Hot Standby](https://www.postgresql.org/docs/18/hot-standby.html) · [Vitess의 샤드 간 조인과 트랜잭션](https://vitess.io/docs/faq/sharding/advanced/can-i-use-vitess-to-do-cross-shard-joins-or/)

**꼬리 질문 · 한 DB에서 테이블만 파티셔닝해도 서버를 늘린 효과가 있나요?**

한 인스턴스의 테이블 파티셔닝은 조건에 맞지 않는 파티션을 건너뛰거나 오래된 데이터를 정리하는 데 도움이 됩니다. 쓰기 연산이 같은 인스턴스의 CPU와 I/O를 계속 사용한다면 서버 수와 쓰기 용량이 분산되지는 않습니다. 처리량이 막힌 자원이 어디인지 확인한 뒤 인스턴스 분할 비용과 비교합니다. [PostgreSQL 선언적 테이블 파티셔닝](https://www.postgresql.org/docs/18/ddl-partitioning.html)

## 31. 일부 NoSQL 시스템은 왜 스케일 아웃에 유리한가요?

**30–60초 답변**

> 분산을 전제로 설계된 키-값 DB는 키로 데이터가 있는 파티션을 결정하고, 조회나 갱신을 담당 파티션으로 보낼 수 있습니다. 요청 대부분이 키로 대상을 정확히 찾고 파티션 간 부하가 고르면 서버를 늘려 저장 공간과 처리량을 나눌 수 있습니다. 함께 조회할 데이터를 한 항목이나 파티션에 모으면 샤드 간 조율도 줄어듭니다. 특정 고객이나 최신 시간 버킷에 요청이 몰리면 서버 전체에 여유가 있어도 해당 키나 파티션이 병목이 될 수 있습니다. [DynamoDB 파티션 키 부하 분산](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html) · [DynamoDB 모델링 기초](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/data-modeling-foundations.html)

**꼬리 질문 · 인기 상품 하나에 쓰기가 집중되면 어떤 비용을 고려하나요?**

여러 레코드로 합산할 수 있는 조회 수처럼 작업 특성이 허용한다면 논리 키에 접미사를 붙여 쓰기를 여러 키로 나눌 수 있습니다. 전체 조회 수를 구할 때는 여러 키를 읽어 합쳐야 합니다. 재고처럼 하나의 상한을 엄격히 지켜야 하는 값은 키를 나눌 경우 상한을 함께 관리하는 방법이 필요합니다. [DynamoDB 쓰기 샤딩](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html)

## 32. MySQL과 PostgreSQL은 어떤 기준으로 비교하나요?

**30–60초 답변**

> 둘 다 관계형 DB지만 기본 동작과 사용할 수 있는 기능이 다릅니다. MySQL 8.4 InnoDB의 기본 격리 수준은 `REPEATABLE READ`이고 PostgreSQL 18의 기본은 `READ COMMITTED`입니다. 트랜잭션에서 같은 조회를 반복하는 코드라면 스냅샷과 락 규칙을 확인합니다. JSON에서 PostgreSQL은 `jsonb`에 GIN 인덱스를 적용할 수 있고, MySQL은 추출한 값에 생성 컬럼이나 함수 인덱스를 사용할 수 있습니다. 채택할 때는 실제 조인과 정렬, JSON 검색, 동시 갱신을 대표 데이터로 재현한 뒤 장애 대응과 백업·복구 운영 경험도 함께 봅니다. [MySQL 8.4 InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html) · [PostgreSQL 18 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html) · [PostgreSQL `jsonb` 인덱싱](https://www.postgresql.org/docs/18/datatype-json.html#JSON-INDEXING) · [MySQL 8.4 `CREATE INDEX`](https://dev.mysql.com/doc/refman/8.4/en/create-index.html)

**꼬리 질문 · MySQL에서 PostgreSQL로 옮길 때 우선 검증할 것은 무엇인가요?**

타입과 기본값, 쿼리 방언, 정렬과 문자열 비교, 트랜잭션 경합에서 달라지는 결과를 확인합니다. 동일한 대표 데이터로 업무 쿼리를 실행해 결과와 계획을 비교하고, 쓰기를 동시에 실행해 성공·대기·재시도 경로도 검증합니다. 예를 들어 순서가 필요한 조회는 `ORDER BY`를 명시하고 테스트에서 의도한 정렬 기준을 확인합니다. [PostgreSQL `ORDER BY`](https://www.postgresql.org/docs/18/queries-order.html) · [애플리케이션에서 확인할 PostgreSQL 격리 동작](https://www.postgresql.org/docs/18/transaction-iso.html)

## 33. CAP 정리는 무엇인가요?

**30–60초 답변**

> CAP의 C는 연산이 실제 시간 순서를 지키며 하나의 복사본에서 일어난 것처럼 보이는 선형화 가능성입니다. A는 장애가 나지 않은 노드가 받은 요청마다 결국 유효한 응답을 준다는 보장입니다. P는 노드 사이의 메시지 전달이 끊기는 상황도 시스템의 동작 범위에 포함한다는 조건입니다. 네트워크 분할로 노드 간 메시지가 전달되지 않는 동안, 분리된 두 노드가 모두 응답하면서 최신 쓰기가 읽기에 반영된다고 항상 보장할 수는 없습니다. 예를 들어 한쪽에서 쓰기가 완료된 뒤 다른 쪽에서 읽으면, 다른 쪽은 그 값을 전달받을 수 없습니다. 그 읽기가 새 값을 확인할 때까지 기다리거나 거절하면 가용성을 제한하고, 이전 값을 반환하면 선형화 가능성을 포기하게 됩니다. [Gilbert와 Lynch의 CAP 설명](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf)

**꼬리 질문 · HTTP `503`을 바로 돌려줘도 CAP 가용성을 충족하나요?**

조회 작업이 성공적으로 값을 반환해야 하는 모델이라면, `503`은 조회에 필요한 값을 제공하지 못했음을 알리는 응답입니다. CAP의 가용성과 운영의 응답 시간 목표를 함께 이야기할 때는 무엇을 유효한 응답으로 보는지 정합니다. [Gilbert와 Lynch의 가용성 정의](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf)

## 34. 실무에서는 네트워크 분할 중 일관성과 가용성 중 무엇을 우선하나요?

**30–60초 답변**

> 기능별로 잘못된 값을 받아들이는 비용과 요청을 처리하지 못하는 비용을 비교합니다. 예를 들어 같은 쿠폰은 한 번만 사용해야 한다면, 권위 있는 쓰기 경로가 확인되는 곳에서만 사용 확정을 받고 확인이 불가능한 곳은 일시 실패로 처리합니다. 상품 설명은 최근 값이 몇 분 늦어도 괜찮다면 로컬 복제본에서 읽도록 해 조회를 이어갈 수 있습니다. 양쪽 쓰기를 받아야 한다면 충돌 병합 규칙과 복구 뒤 수렴 조건이 업무 규칙을 만족하는지 정해야 합니다. [Gilbert와 Lynch의 CAP와 약한 일관성](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf)

**꼬리 질문 · 사용자가 쿠폰을 쓴 직후 조회에서 사용 여부가 안 보이면요?**

쿠폰 사용이 완료된 세션의 후속 조회를 최신 상태를 확인할 수 있는 경로로 보냅니다. 읽기 복제본에서 제공하려면 해당 쓰기 시점까지 반영됐는지 확인할 수 있는 기준을 둡니다. 그 상태를 확인할 수 없을 때는 이전 값으로 사용 여부를 추정하기보다 확인 중으로 표시하고 재조회할 수 있게 합니다. [PostgreSQL Hot Standby의 반영 지연](https://www.postgresql.org/docs/18/hot-standby.html)
