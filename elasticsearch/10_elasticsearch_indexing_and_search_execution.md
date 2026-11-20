# Elasticsearch Indexing and Search Execution

문서가 쓰기 요청을 받은 뒤 언제 ID로 보이고 언제 검색에 나타나는지 확인한다. 검색 단계에서는 매핑과 분석기가 어떤 일치 조건을 만드는지 살펴본다.

## 1. 색인 요청에서 검색 가능한 세그먼트까지

1. 조정 노드는 인덱스와 라우팅 값을 해석해 프라이머리 샤드로 쓰기를 보낸다.
2. 프라이머리는 매핑을 적용해 필드를 파싱하고 `text`를 분석한다. 쿼리에 사용하는 용어와 필드 값은 Lucene이 저장한다.
3. 프라이머리는 쓰기를 동기 상태의 레플리카에 전달한다. 기본 `request` 내구성 설정에서는 성공으로 응답하기 전에 관련 사본의 translog를 디스크에 동기화한다.
4. Refresh가 새 세그먼트를 검색에 보이게 한다. Flush는 Lucene 커밋을 만들고 새 translog 세대를 시작한다. Merge는 작은 세그먼트를 더 큰 세그먼트로 합친다.

검색에서 보이는 시점과 재시작 후 쓰기를 복구할 수 있는 시점은 서로 다른 설정과 동작에 의해 결정된다. [읽기와 쓰기](https://www.elastic.co/docs/deploy-manage/distributed-architecture/reading-and-writing-documents) · [Near real-time search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search) · [Translog 설정](https://www.elastic.co/docs/reference/elasticsearch/index-settings/translog)

## 2. 실시간 GET과 리프레시 재현

실습 인덱스의 자동 refresh를 잠시 끈다. 첫 `_search`는 0건이며, ID 조회는 이미 쓰인 문서를 읽는다. 수동 refresh 후에는 같은 검색이 1건을 반환한다.

```http
PUT /es-execution-lab
{
  "settings":{"number_of_replicas":0,"refresh_interval":"-1"},
  "mappings":{
    "properties":{
      "title":{"type":"text","fields":{"raw":{"type":"keyword"}}},
      "sku":{"type":"keyword"}
    }
  }
}

PUT /es-execution-lab/_doc/1
{"title":"Mechanical Keyboard","sku":"KEY-100"}

GET /es-execution-lab/_doc/1

GET /es-execution-lab/_search
{"query":{"match":{"title":"keyboard"}}}

POST /es-execution-lab/_refresh

GET /es-execution-lab/_search
{"query":{"match":{"title":"keyboard"}}}

PUT /es-execution-lab/_settings
{"index":{"refresh_interval":null}}
```

일반 API에서 새 문서를 곧바로 검색해야 할 때는 `refresh=wait_for`로 다음 refresh를 기다릴 수 있다. 자동 refresh를 꺼 둔 위 실습에서는 직접 refresh하기 전까지 이 대기가 길어질 수 있다. [Refresh parameter](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/refresh-parameter)

## 3. 검색의 query 단계와 fetch 단계

기본 `query_then_fetch` 방식에서 조정 노드는 각 대상 샤드의 사본 하나에 검색을 분산한다. Query 단계에서 각 샤드는 조건을 만족하는 상위 후보와 정렬 값을 돌려준다. 조정 노드는 전체 상위 결과를 정한 다음 fetch 단계에서 필요한 문서 내용을 가져온다. `_shards.failed`와 `timed_out`을 함께 읽어 일부 샤드의 실패나 시간 초과를 확인한다. [Search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search)

| 필드 | 검색 방식 | 대표 사용처 |
| --- | --- | --- |
| `text` | `match`가 검색어를 분석해 색인된 용어와 비교한다. | 이름·설명 전문 검색 |
| `keyword` | `term`이 색인된 전체 용어를 비교한다. 별도 정규화 설정이 없으면 대소문자가 구분된다. | ID·코드 필터, 정렬, 집계 |

```http
GET /es-execution-lab/_search
{"query":{"match":{"title":"KEYBOARD"}}}

GET /es-execution-lab/_search
{"query":{"term":{"sku":"KEY-100"}}}

GET /es-execution-lab/_search
{"query":{"term":{"sku":"key-100"}}}

GET /es-execution-lab/_search
{"query":{"term":{"title.raw":"Mechanical Keyboard"}}}
```

위 결과는 각각 1건, 1건, 0건, 1건이다. 같은 값을 전문 검색과 정확 일치로 모두 써야 하면 `title`과 `title.raw`처럼 멀티 필드에 각각 색인한다. [Text 필드](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/text) · [Keyword 계열 필드](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/keyword)
