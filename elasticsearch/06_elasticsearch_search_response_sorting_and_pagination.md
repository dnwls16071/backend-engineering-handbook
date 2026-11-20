# Elasticsearch Search Responses, Sorting, and Pagination

검색 결과에서 보여 줄 필드와 페이지 순서를 정한다. 아래 예제는 [카탈로그 데이터](03_elasticsearch_text_analysis_and_field_mapping.md)를 사용한다.

## 1. YAML 출력과 필드 선택

`format=yaml`로 응답 표현을 바꾼다. `filter_path`는 응답 JSON 구조에서 남길 경로를 선택하고, `_source`는 히트 안에서 반환할 원본 필드를 선택한다.

```http
GET /es-catalog/_search?format=yaml&filter_path=hits.hits._id,hits.hits._source
{
  "size":2,
  "_source":{"includes":["productId","title","price"],"excludes":["offers.*"]},
  "query":{"match_all":{}}
}
```

Console에서 출력 형식을 보기 어렵다면 터미널에서 확인한다.

```bash
curl -fsS "$ES_URL/es-catalog/_search?format=yaml&size=1&_source=title,price"
```

원본이 필요 없으면 `_source:false`로 응답에서 생략할 수 있다. 매핑에 따른 형식이나 선택한 doc values가 필요하면 `fields` 또는 `docvalue_fields`를 검토한다. 응답에서 제외하는 설정은 필드 단위 권한 관리에 쓰지 않는다. [일반 REST 옵션](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/common-options) · [선택한 필드 조회](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrieve-selected-fields)

## 2. 정렬과 페이지 이동

작은 페이지 번호에는 `from`과 `size`를 사용한다. `from`은 건너뛸 결과 수다. 정렬은 `price` 오름차순이며, 가격이 같으면 고유한 `productId`로 순서를 고정한다. 가격 35인 `p2`와 `p3` 중 첫 페이지의 결과는 `p2`다.

```http
GET /es-catalog/_search
{
  "from":0,
  "size":1,
  "sort":[{"price":"asc"},{"productId":"asc"}],
  "_source":["productId","price"]
}

GET /es-catalog/_search
{
  "size":1,
  "sort":[{"price":"asc"},{"productId":"asc"}],
  "search_after":[35,"p2"],
  "_source":["productId","price"]
}
```

두 번째 요청은 다음 결과 `p3`를 반환한다. `search_after`에는 이전 페이지 마지막 히트의 `sort` 배열을 그대로 넣고 쿼리와 정렬 조건을 유지한다. 문자열 정렬에는 `title.raw` 같은 `keyword` 필드를 쓴다.

깊은 페이지에서는 각 샤드가 앞 페이지의 히트까지 준비해야 하므로 `from + size`의 기본 결과 윈도는 10,000이다. 페이지 사이에 문서가 바뀔 수 있다면 PIT를 열고 `POST /_search`에 `pit`과 `search_after`를 전달한다. 응답의 최신 PIT ID와 마지막 히트의 전체 정렬 값을 다음 요청에 넘기고, 순회가 끝나면 PIT를 닫는다. [검색 결과 정렬](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/sort-search-results) · [검색 결과 페이지네이션](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results)
