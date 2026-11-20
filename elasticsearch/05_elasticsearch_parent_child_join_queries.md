# Elasticsearch Parent-Child Join Queries

`join` 필드는 같은 인덱스에서 서로 다른 문서로 저장되는 부모와 자식을 연결한다. 부모와 자식은 같은 샤드에 있어야 한다. 자식이 많고 각자 갱신되는 경우를 검토할 수 있다. 읽기가 중심이라면 중복을 허용한 문서 설계가 조인 비용을 줄일 수 있다. [Join field](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/parent-join)

## 1. 같은 샤드에 문서 저장

가이드 한 개와 댓글 두 개를 생성한다. 모든 문서의 라우팅 값은 부모 ID인 `guide-1`이다. 문서를 ID로 조회하거나 수정할 때도 같은 라우팅 값을 쓴다.

```http
PUT /es-join-lab
{
  "settings":{"number_of_shards":2,"number_of_replicas":0},
  "mappings":{
    "_routing":{"required":true},
    "properties":{
      "title":{"type":"text"},
      "body":{"type":"text"},
      "relation":{"type":"join","relations":{"guide":"comment"}}
    }
  }
}

PUT /es-join-lab/_doc/guide-1?routing=guide-1
{"title":"Elasticsearch Query Guide","relation":"guide"}

PUT /es-join-lab/_doc/comment-1?routing=guide-1
{"body":"Pagination with a cursor","relation":{"name":"comment","parent":"guide-1"}}

PUT /es-join-lab/_doc/comment-2?routing=guide-1&refresh=wait_for
{"body":"Exact category filters","relation":{"name":"comment","parent":"guide-1"}}
```

## 2. 부모와 자식을 검색

`parent_id`는 부모 ID에 속한 자식 문서를 찾는다. `has_child`는 자식이 조건을 만족하는 부모를, `has_parent`는 부모가 조건을 만족하는 자식을 찾는다. `inner_hits`로 상위 검색 결과에 어떤 관련 문서가 일치했는지 포함할 수 있다.

```http
GET /es-join-lab/_search?routing=guide-1
{"query":{"parent_id":{"type":"comment","id":"guide-1"}}}

GET /es-join-lab/_search
{
  "query":{
    "has_child":{
      "type":"comment",
      "query":{"match":{"body":"pagination"}},
      "inner_hits":{"size":2}
    }
  }
}

GET /es-join-lab/_search
{
  "query":{
    "has_parent":{
      "parent_type":"guide",
      "query":{"match":{"title":"elasticsearch"}}
    }
  }
}
```

두 번째 요청은 `guide-1`을 반환하며 해당 결과의 `inner_hits`에 `comment-1`이 들어간다. `nested`는 배열 요소를 부모 문서 안에 저장하는 방식이고, `join`은 문서가 자체 ID와 라우팅을 가진다. [Parent ID query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-parent-id-query) · [Joining queries](https://www.elastic.co/docs/reference/query-languages/query-dsl/joining-queries)
