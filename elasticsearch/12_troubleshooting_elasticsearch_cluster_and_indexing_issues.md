# Troubleshooting Elasticsearch Cluster and Indexing Issues

장애가 시작된 시각, 영향받은 인덱스·별칭, 요청의 HTTP 상태와 `error.type`을 먼저 기록한다. 실패한 Bulk라면 동일한 요청의 항목별 응답도 확보한다. [모니터링 지표](11_monitoring_elasticsearch_with_cat_apis_and_node_stats.md)를 같은 시간대와 비교하고 관찰한 원인에 맞춰 복구한다.

## 1. 클러스터가 yellow 또는 red일 때

`yellow`는 레플리카가 미할당된 상태다. `red`는 프라이머리도 미할당된 상태라 해당 샤드의 데이터에 접근하지 못할 수 있다. 어떤 샤드가 빠졌는지 확인하고, 노드 목록과 로그에서 이탈·재시작 시각을 대조한다.

```http
GET /_cluster/health?level=indices&filter_path=status,unassigned_shards,indices.*.status,indices.*.unassigned_shards

GET /_cat/shards?v=true&h=index,shard,prirep,state,node,unassigned.reason&s=state

GET /_cat/nodes?v=true&h=name,node.role,master
```

노드가 복귀했다면 초기화·할당 과정에서 미할당 샤드 수가 감소하는지 확인한다. 프라이머리의 정상 사본이 없으면 복구 가능한 노드와 스냅샷을 확인한다. [Red or yellow cluster health](https://www.elastic.co/docs/troubleshoot/elasticsearch/red-yellow-cluster-status)

## 2. 문서를 색인할 수 없을 때

`cluster_block_exception`이면 인덱스의 쓰기 블록과 디스크 상태를 확인한다. Flood-stage를 넘으면 Elasticsearch는 해당 노드에 샤드가 있는 인덱스에 `index.blocks.read_only_allow_delete`를 설정한다. 디스크 여유를 확보해 사용량이 high watermark 아래로 내려가면 Elasticsearch가 자동으로 설정한 블록을 해제한다. `403`은 권한 오류에도 쓰이므로 오류 본문의 타입과 이유를 읽는다. 매핑 오류라면 문서와 타입을, `429`라면 [쓰기 거절 지표](13_diagnosing_elasticsearch_write_thread_pool_rejections.md)를 확인한다. [Disk watermark errors](https://www.elastic.co/docs/troubleshoot/elasticsearch/fix-watermark-errors) · [Index blocks](https://www.elastic.co/docs/reference/elasticsearch/index-settings/index-block)

아래 예제는 별도의 로컬 인덱스에 임시 쓰기 블록을 설정한다. 첫 번째 문서 색인은 `cluster_block_exception`을 반환한다. `null`로 수동 블록을 초기화하면 같은 요청이 성공한다.

```http
PUT /es-troubleshoot-lab
{
  "settings":{"number_of_replicas":0},
  "mappings":{"dynamic":"strict","properties":{"title":{"type":"keyword"}}}
}

PUT /es-troubleshoot-lab/_settings
{"index.blocks.write":true}

GET /es-troubleshoot-lab/_settings?filter_path=*.settings.index.blocks

PUT /es-troubleshoot-lab/_doc/blocked
{"title":"Index write check"}

PUT /es-troubleshoot-lab/_settings
{"index.blocks.write":null}

PUT /es-troubleshoot-lab/_doc/blocked?refresh=wait_for
{"title":"Index write check"}
```

## 3. 일부 문서만 간헐적으로 검색에서 빠질 때

| 확인 결과 | 다음 점검 |
| --- | --- |
| Bulk 응답의 `errors:true` | `items[]`에서 실패한 ID·상태·오류 이유를 확인한다. 요청 전체가 성공 응답을 받아도 개별 문서가 빠질 수 있다. |
| ID 조회는 성공하고 검색만 실패 | refresh 시점, 검색 대상 별칭과 필터, 분석 결과를 확인한다. |
| ID 조회도 실패하거나 타임아웃 | 쓰기 대상·ID·라우팅을 대조한다. 타임아웃 직후에는 서버에서 처리됐을 가능성도 확인한다. |
| 검색 응답에 샤드 오류 또는 시간 초과 | `_shards.failed`, `_shards.failures`와 `timed_out`을 확인한다. |

같은 로컬 인덱스에 두 항목을 보낸다. 첫 문서는 저장되고, 두 번째는 `dynamic:strict`에 등록하지 않은 필드 때문에 거절된다. [Bulk API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk) · [Refresh parameter](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/refresh-parameter)

```http
POST /es-troubleshoot-lab/_bulk?refresh=wait_for
{"index":{"_id":"valid"}}
{"title":"Valid document"}
{"index":{"_id":"invalid"}}
{"title":"Invalid document","unexpectedField":true}

GET /es-troubleshoot-lab/_doc/valid
```

## 4. 샤드를 배치할 수 없을 때

`unassigned.reason`은 샤드가 미할당 상태가 된 계기다. 현재 배치를 막는 제약은 `_cluster/allocation/explain`의 `deciders`에서 찾는다. [01번 단일 노드 실습](01_elasticsearch_fundamentals_and_cluster_architecture.md)에서는 같은 샤드 사본을 한 노드에 배치할 수 없어서 `same_shard`가 나온다.

```http
GET /_cluster/allocation/explain?filter_path=index,shard,primary,current_state,can_allocate,node_allocation_decisions.node_name,node_allocation_decisions.deciders
{"index":"es-shard-lab","shard":0,"primary":false}

GET /_cluster/settings?include_defaults=true&filter_path=*.cluster.routing.allocation.enable
```

`disk_threshold`가 거절하면 디스크 여유를, 필터나 데이터 티어 결정이 거절하면 해당 조건에 맞는 노드를 확인한다. 유지보수 뒤라면 할당을 제한한 설정이 남아 있는지도 본다. 원인을 해결한 뒤 대상 샤드의 상태를 다시 확인한다. [Cluster allocation explain API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-allocation-explain) · [Shard allocation settings](https://www.elastic.co/docs/reference/elasticsearch/configuration-reference/cluster-level-shard-allocation-routing-settings)

## 5. GC가 자주 발생할 때

한 번의 힙 사용률보다 Old 영역이 GC 후에도 계속 높은지 확인한다. 두 번의 표본에서 `collection_count`와 `collection_time_in_millis`의 증가량을 비교하고, 요청 지연과 로그의 GC overhead 메시지가 같은 시간대인지 확인한다.

```http
GET /_nodes/stats/jvm?filter_path=nodes.*.name,nodes.*.jvm.mem.pools.old,nodes.*.jvm.gc.collectors

GET /_nodes/hot_threads?type=cpu&threads=5&ignore_idle_threads=true
```

GC가 길어진 시간대에 큰 Bulk, 동시 요청 증가, 비용이 큰 검색·집계, 샤드 수 증가가 있었는지 확인한다. 실제 부하 원인을 줄인 뒤 같은 구간의 GC 시간과 지연을 비교한다. [High JVM memory pressure](https://www.elastic.co/docs/troubleshoot/elasticsearch/high-jvm-memory-pressure)
