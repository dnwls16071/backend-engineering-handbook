# Elasticsearch Document Operations and Concurrency

[Docker 실습 환경](01_elasticsearch_fundamentals_and_cluster_architecture.md)에서 문서별 CRUD, 라우팅, 복제와 동시성 제어를 확인한다.

## 1. 생성, 조회, 수정, 교체

```http
PUT /es-docs-lab
{
  "settings": {"number_of_shards": 2, "number_of_replicas": 0},
  "mappings": {
    "_routing": {"required": true},
    "properties": {
      "title": {"type": "text"},
      "status": {"type": "keyword"},
      "stock": {"type": "integer"}
    }
  }
}

PUT /es-docs-lab/_create/book-1?routing=store-a&refresh=wait_for
{"title":"Search Guide","status":"draft","stock":4}

GET /es-docs-lab/_doc/book-1?routing=store-a

POST /es-docs-lab/_update/book-1?routing=store-a
{"doc":{"status":"active"}}

POST /es-docs-lab/_update/book-1?routing=store-a
{
  "script": {
    "source": "ctx._source.stock += params.amount",
    "params": {"amount": 2}
  }
}

POST /es-docs-lab/_update/book-2?routing=store-a
{"doc":{"title":"Index Guide","status":"active","stock":2},"doc_as_upsert":true}

PUT /es-docs-lab/_doc/book-2?routing=store-a&refresh=wait_for
{"title":"Index Guide, Second Edition","status":"active","stock":3}
```

`_create`는 같은 ID와 라우팅으로 이미 존재하는 문서에 `409`를 반환한다. `_update`의 `doc`은 일부 필드를 바꾸고, `doc_as_upsert`는 문서가 없으면 그 내용을 새 문서로 저장한다. 기존 문서에 스크립트를 실행하고 없는 문서에는 별도 초기값을 쓰려면 `script`와 `upsert`를 함께 지정할 수 있다. 반면 `PUT /_doc/{id}`는 전달한 본문 전체로 문서를 교체하므로 빠뜨린 필드는 남지 않는다. [Index API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-index) · [Update API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-update)

## 2. 읽기, 쓰기, 라우팅

일반적으로 Elasticsearch는 문서 ID로 샤드를 결정한다. 사용자 지정 `routing`을 쓴 문서는 조회·수정·삭제에 같은 값을 써야 한다. 검색에 라우팅을 지정하면 대상 샤드를 좁힐 수 있다. 같은 샤드에 다른 라우팅 값의 문서도 함께 있을 수 있으므로, 라우팅 값만으로 접근 권한을 구현하지 않는다.

쓰기 요청은 대상 샤드의 프라이머리에서 처리되고 동기 상태의 복제본으로 전달된다. `wait_for_active_shards`는 쓰기 전에 필요한 활성 샤드 사본 수를 검사한다. ID로 읽는 `GET /_doc`은 기본적으로 실시간이고, `_search`는 리프레시 이후 새 문서를 찾는다. 쓰기 직후 검색해야 하는 예제에서는 `refresh=wait_for`를 지정한다. [읽기와 쓰기](https://www.elastic.co/docs/deploy-manage/distributed-architecture/reading-and-writing-documents) · [라우팅 필드](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/mapping-routing-field) · [리프레시 매개변수](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/refresh-parameter)

## 3. 낙관적 동시성 제어

문서를 조회한 응답에서 `_seq_no`와 `_primary_term`을 읽는다. 아래 `SEQ`와 `TERM`을 그 값으로 바꾼다. 그사이 다른 쓰기가 먼저 발생했다면 이 요청이 `409`로 끝난다. 이때 최신 문서를 다시 읽고 변경 의도를 재적용할지 결정한다.

```http
GET /es-docs-lab/_doc/book-1?routing=store-a

POST /es-docs-lab/_update/book-1?routing=store-a&if_seq_no=SEQ&if_primary_term=TERM
{"doc":{"stock":5}}
```

카운터 증가처럼 최신 문서에 다시 적용해도 되는 작업에는 `retry_on_conflict`를 검토한다. 사용자가 읽은 값에 근거해 덮어쓰는 작업은 조건부 갱신을 사용한다. [낙관적 동시성 제어](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/optimistic-concurrency-control)

## 4. 쿼리 기반 일괄 변경과 Bulk

`_update_by_query`와 `_delete_by_query`는 시작 시점의 검색 스냅샷에서 대상을 찾는다. 버전 충돌과 부분 실패를 확인한다. Bulk는 한 요청에서 여러 작업을 보내며 각 항목의 성공 여부를 따로 반환한다.

```http
POST /es-docs-lab/_bulk?refresh=wait_for
{"index":{"_id":"book-3","routing":"store-a"}}
{"title":"Query Guide","status":"draft","stock":1}
{"update":{"_id":"book-2","routing":"store-a"}}
{"doc":{"stock":7}}

POST /es-docs-lab/_update_by_query?refresh=true
{
  "query":{"term":{"status":"draft"}},
  "script":{"source":"ctx._source.status = params.status","params":{"status":"archived"}}
}

POST /es-docs-lab/_delete_by_query?refresh=true
{"query":{"term":{"status":"archived"}}}

DELETE /es-docs-lab/_doc/book-2?routing=store-a&refresh=wait_for
```

삭제 전에는 동일한 조건으로 `_search`나 `_count`를 실행해 대상을 확인한다. Console 밖에서 Bulk API를 호출할 때는 `Content-Type: application/x-ndjson`과 `--data-binary @bulk.ndjson`을 사용한다. 각 작업과 본문을 한 줄씩 쓰고 마지막에 줄바꿈을 둔다. HTTP 요청이 성공해도 응답의 `errors`와 `items`를 확인한다. [Bulk API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk) · [Update by query](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-update-by-query) · [Delete by query](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-delete-by-query)
