# Partitioning and Sharding Order Data

주문이 쌓이면 먼저 어떤 쿼리가 느려졌고 어떤 자원이 포화됐는지 확인한다. 주문 조회는 사용자별 최신 목록과 운영팀이 날짜 범위로 조회하는 전체 사용자 주문을 예로 든다. 예제에서 `created_at`은 주문 생성 후 고정되고 `order_id`는 전역에서 유일하다고 가정한다. 두 컬럼에는 `NULL`이 들어가지 않는다.

## 1. 테이블 파티셔닝과 샤딩은 어떻게 다른가?

> 테이블 파티셔닝은 큰 테이블을 여러 조각으로 나눠 관리하는 방법입니다. 월별로 나누면 특정 월을 조회할 때 해당 파티션만 읽고 오래된 월은 파티션 단위로 정리할 수 있습니다. 샤딩은 주문을 여러 DB 인스턴스에 배치해 저장 용량과 쓰기 부하를 분산합니다. [PostgreSQL · Table Partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html) · [Vitess · Sharding Guidelines](https://vitess.io/docs/24.0/user-guides/vschema-guide/sharding-guidelines/)

- **파티션 프루닝은 언제 되나요?** 월별 파티션에서 `created_at >= :from AND created_at < :to`로 경계를 주면 조건과 겹치지 않는 파티션을 제외할 수 있습니다. 파티션 경계로 읽을 파티션을 결정하고, 선택한 파티션 안에서는 비용에 따라 인덱스나 테이블 스캔을 사용합니다. [PostgreSQL · Partition Pruning](https://www.postgresql.org/docs/18/ddl-partitioning.html#DDL-PARTITION-PRUNING)
- **파티션을 여러 디스크에 두면 쓰기도 분산되나요?** 한 인스턴스 안에서 디스크 I/O는 나눌 수 있습니다. 그 인스턴스의 CPU, 연결, 트랜잭션 처리와 로그 기록은 계속 공유합니다. PostgreSQL은 파티션별 테이블스페이스를 지원하고 MySQL InnoDB는 파티션별 `DATA DIRECTORY`를 지원합니다. [PostgreSQL · Table Partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html) · [MySQL · Overview of Partitioning](https://dev.mysql.com/doc/refman/8.4/en/partitioning-overview.html)

## 2. 파티션을 나눴는데 왜 쓰기 서버는 하나인가?

> 단일 프라이머리 안에서 월별 파티션을 만들면 같은 프라이머리가 어떤 파티션에 쓸지 결정하고 트랜잭션을 커밋합니다. 파티션을 나누면 읽는 범위를 줄이고 오래된 데이터를 관리하기 쉬워집니다. 쓰기 요청 자체를 여러 서버가 처리해야 한다면 `user_id` 같은 키로 나누고 각 샤드의 프라이머리에 쓰도록 라우팅하겠습니다. [PostgreSQL · Table Partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html) · [Vitess · Sharding Guidelines](https://vitess.io/docs/24.0/user-guides/vschema-guide/sharding-guidelines/)

- **읽기 복제본을 추가하면 어떤 문제가 해결되나요?** 복제 지연을 허용하는 조회를 분산할 수 있습니다. 단일 프라이머리 구성에서는 원본 쓰기가 계속 그 서버로 모입니다. 샤딩으로 해결할 병목인지 판단하려면 피크 시간의 쓰기 지연과 CPU·로그 I/O·락 대기를 확인합니다. [PostgreSQL · Log-Shipping Standby Servers](https://www.postgresql.org/docs/18/warm-standby.html) · [MySQL · Replication](https://dev.mysql.com/doc/refman/8.4/en/replication.html)
- **한 샤드 안에도 월별 파티션을 둘 수 있나요?** 네. 먼저 `user_id`로 DB 인스턴스를 고르고, 그 인스턴스에서 `created_at`으로 월별 파티션을 고릅니다. 날짜 조건으로 각 샤드 안의 파티션은 줄어들고, 사용자가 지정되지 않은 조회의 라우팅 범위는 별도로 결정합니다. [PostgreSQL · Table Partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html)

## 3. `user_id`를 샤드 키로 쓰면 무엇이 달라지는가?

> 사용자 주문 목록을 자주 조회한다면 `user_id`로 한 샤드에 바로 보낼 수 있습니다. 주문과 주문 항목을 같은 샤드에 두면 조인과 트랜잭션도 그 안에서 처리할 수 있습니다. 특정 사용자나 테넌트에 트래픽이 집중된다면 샤드별 행 수와 함께 키별 요청량과 지연을 보겠습니다. [Vitess · Sharding Guidelines](https://vitess.io/docs/24.0/user-guides/vschema-guide/sharding-guidelines/)

- **샤드 안의 인덱스는 어떻게 두나요?** 사용자별 최신 목록에는 `(user_id, created_at DESC, order_id DESC)`를 고려합니다. 샤드 키로 서버를 고른 뒤 복합 인덱스로 그 사용자의 주문을 정렬된 순서로 읽습니다. 여러 샤드가 각자 만든 로컬 고유 인덱스의 제약 범위는 각 샤드입니다. [PostgreSQL · Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html) · [PostgreSQL · Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
- **`order_id`만 들어오면 어떻게 찾나요?** API가 `user_id`도 받게 하거나 `order_id`에서 샤드 키를 찾는 라우팅 인덱스를 둡니다. 라우팅 인덱스를 별도로 저장하면 주문 생성·이동 중 그 인덱스가 어긋났을 때의 조회와 복구 방법도 필요합니다. [Vitess · Vindexes](https://vitess.io/docs/24.0/reference/features/vindexes/)
- **핫 테넌트가 생기면 어떻게 하나요?** 테넌트에 사용자가 여럿이고 보조 키로 요청을 나눌 수 있다면 테넌트 내부를 여러 샤드로 분산합니다. 단일 `user_id` 자체가 뜨겁다면 그 사용자의 주문을 `order_id` 등으로 더 나누는 방안을 검토합니다. 두 경우 모두 상위 단위 전체 조회나 트랜잭션에서 샤드 간 처리가 늘 수 있습니다. 단일 주문 행에 쓰기가 집중되는 경우에는 주문을 나누어 배치해도 그 행의 경합은 남습니다.

## 4. 모든 사용자의 주문을 날짜로 조회하려면?

> `user_id`로 샤딩했다면 날짜 조건만으로는 대상 샤드를 고를 수 없습니다. 각 샤드에 같은 조건과 정렬을 병렬로 보내고, 샤드별 상위 `k`개를 병합해 전체 상위 `k`개를 구하는 스캐터·개더(scatter/gather)를 씁니다. 운영팀 조회가 잦으면 날짜 기준 읽기 모델도 고려하고, 그 모델이 얼마나 늦어져도 되는지 먼저 정하겠습니다. [Vitess · Vindexes](https://vitess.io/docs/24.0/reference/features/vindexes/) · [Elasticsearch · Paginate Search Results](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/paginate-search-results.html)

1. 샤드마다 같은 기간을 적용하고 `ORDER BY created_at DESC, order_id DESC LIMIT :k`로 조회한다. 전체 날짜 조회용 로컬 인덱스로 `(created_at DESC, order_id DESC)`를 고려한다. [PostgreSQL · Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
2. 응답을 모으는 쪽에서 정렬된 목록을 병합한다. 한 샤드에서 `k`등 밖인 행은 같은 샤드에서만 최소 `k`개가 앞서므로 전체 상위 `k`개에도 들어갈 수 없다.
3. 다음 페이지에서는 마지막으로 반환한 `(created_at, order_id)`보다 작은 행만 각 샤드에 요청해 같은 방식으로 병합한다. 두 컬럼은 모두 내림차순이며, `order_id`로 생성 시각이 같은 주문의 순서를 고정한다. [PostgreSQL · Row Constructor Comparison](https://www.postgresql.org/docs/18/functions-comparisons.html#ROW-WISE-COMPARISON) · [Elasticsearch · Search After](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/paginate-search-results.html#search-after)

- **깊은 페이지에서 `OFFSET`을 피하는 이유는요?** 전체에서 `m`개를 건너뛴 뒤 `k`개를 반환하려면 단순 병합 방식에서는 샤드마다 최대 `m + k`개를 가져와야 합니다. 커서로 조회하면 이전 페이지의 행을 샤드마다 다시 가져오는 비용을 줄입니다. 페이지마다 동일한 데이터 집합이 필요하면 커서에 더해 일관된 스냅샷이나 조회 기준을 정해야 합니다. [PostgreSQL · LIMIT and OFFSET](https://www.postgresql.org/docs/18/queries-limit.html) · [Elasticsearch · Open a Point in Time](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-open-point-in-time)
- **일부 샤드가 늦거나 실패하면요?** 정확한 전체 결과가 필요하면 해당 샤드까지 기다리되 마감 시간을 두고, 실패 시 조회를 실패 처리하거나 재시도합니다. 부분 결과를 허용하는 관리 화면이라면 어떤 샤드가 빠졌는지 표시합니다. 누락된 샤드에 가장 최신 주문이 있을 수 있습니다.

## 5. 범위 샤딩과 해시 샤딩 중 어떻게 고르는가?

> 범위 샤딩은 키의 순서를 보존해서 기간이나 ID 구간 질의에 유리합니다. 주문 생성 시각을 기준으로 나누면 가장 최근 범위에 새 쓰기가 몰릴 수 있습니다. `user_id` 해시 샤딩은 여러 사용자의 쓰기를 흩뜨리기 좋습니다. 특정 사용자 하나에 주문이 몰릴 때는 그 키를 더 작은 단위로 나누는 방안을 검토합니다. [Bigtable · Schema Design Best Practices](https://docs.cloud.google.com/bigtable/docs/schema-design) · [Dynamo §4.2, §6.2](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)

| 배치 방식 | 잘 맞는 접근 패턴 | 부하가 집중되는 경우 |
| --- | --- | --- |
| 범위 샤딩 | 정렬된 키의 구간 조회. `created_at`으로 나누면 겹치는 날짜 구간에만 요청할 수 있다. | 단조 증가 키의 최신 구간 또는 인기 키가 모인 범위 |
| 해시 샤딩 | 해시 입력 전체를 아는 동등 조회. `user_id`를 알고 있으면 사용자 주문을 한 샤드에서 조회한다. | 한 키의 부하가 매우 크거나 해시 결과의 샤드 배정이 불균등한 경우 |

- **분포가 좋다는 것을 어떻게 확인하나요?** 샤드별 데이터 크기, 쓰기·읽기 처리량, p99 지연과 가장 뜨거운 키를 봅니다. 키 개수가 비슷해도 주문 수와 조회 빈도는 크게 다를 수 있습니다.

## 6. 샤드를 추가할 때 얼마나 이동하고 어떻게 전환하는가?

> `hash(key) % N`에서 분모를 바꾸면 기존 샤드끼리도 데이터가 많이 움직입니다. 확장이 잦다면 일관 해싱으로 새 노드가 맡는 구간만 옮기거나, 고정 논리 버킷을 두고 일부 버킷의 소유 노드만 바꾸겠습니다. 전환할 때는 데이터를 복사하고, 이전 소유자의 쓰기를 막은 시점까지 변경분을 적용한 뒤 라우팅을 바꿉니다. [Karger 외 · Consistent Hashing](https://people.csail.mit.edu/karger/Papers/web.pdf) · [Dynamo §6.2](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html) · [Vitess · Reshard](https://vitess.io/docs/24.0/reference/vreplication/reshard/)

- **`N → N + 1`이면 몇 퍼센트가 움직이나요?** 같은 해시와 기존 노드 번호 `0`부터 `N - 1`까지를 유지하고, 해시가 `N(N + 1)`개의 나머지에 균등하게 퍼진다고 가정합니다. 두 나머지가 같은 경우는 한 주기에 `N`개라 유지되는 비율이 `1 / (N + 1)`입니다. 따라서 이동하는 키의 비율은 약 `N / (N + 1)`입니다. `4 → 5`라면 약 80%입니다. 실제 바이트 이동량은 키별 데이터 크기에 따라 달라집니다.
- **일관 해싱과 가상 노드는 어떻게 동작하나요?** 해시 링에서 키부터 시계 방향으로 처음 만나는 토큰의 노드가 해당 키를 맡습니다. 기존 토큰 위치를 고정하고 새 토큰을 넣으면 그 토큰이 맡게 된 구간의 기본 소유자만 바뀝니다. 물리 노드마다 여러 토큰인 가상 노드를 두면 구간과 부하를 여러 곳에 나눌 수 있습니다. 실제 이동량은 토큰 배치·데이터 분포·복제 배치에 따라 달라집니다. [Karger 외 · Consistent Hashing](https://people.csail.mit.edu/karger/Papers/web.pdf) · [Dynamo §4.2–4.3](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
- **고정 논리 버킷은 어떤 방식인가요?** 예를 들어 `hash(user_id) % 1024`로 버킷을 고정하고, `bucket → shard` 매핑에서 물리 위치를 결정합니다. 4대에서 5대로 늘릴 때 선택한 버킷의 소유자만 매핑에서 바꾸면 됩니다. 버킷별 데이터 크기와 부하를 보고 이동 대상을 고를 수 있습니다. [Dynamo §6.2](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)

**안전한 리밸런싱 순서**

1. 이전 소유자가 쓰기를 받는 동안 로그 위치와 연결된 스냅샷을 새 샤드에 복사한다. 이후 변경분을 로그나 CDC로 새 샤드에 적용하며 진도를 기록한다.
2. 전환 시 이전 소유자의 해당 범위 쓰기를 차단하고, 진행 중인 쓰기를 마무리한 마지막 로그 위치까지 새 샤드가 따라잡도록 한다. 데이터와 로그 적용 지점을 검증한다.
3. 버킷 소유권과 라우팅 버전(epoch)을 함께 갱신하고 새 소유자에서 쓰기를 연다. 저장 경로에서 소유권이나 epoch를 검증해 예전 라우팅으로 보낸 쓰기를 거절한다. 라우터는 매핑을 새로 읽고 같은 요청 식별자로 재시도한다.
4. 전환 후 누락과 지연을 확인한다. 되돌릴 수 있는 기간이 필요하면 새 샤드의 변경분을 이전 샤드에도 반영할 경로를 유지한다. 되돌릴 때도 쓰기 차단과 변경분 추격을 거쳐야 한다. [Vitess · Reshard](https://vitess.io/docs/24.0/reference/vreplication/reshard/) · [Chubby §2.4](https://research.google.com/archive/chubby-osdi06.pdf)
