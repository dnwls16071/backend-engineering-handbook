# Designing Metadata Filters and Document Constraints

where는 메타데이터 조건을, where_document는 본문 조건을 받는다. 둘 다 후보를 고르는 필터로 사용할 수 있다. [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) · [Chroma · Full Text Search](https://docs.trychroma.com/docs/querying-collections/full-text-search) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 1. 검색 조건과 소유·권한 정보를 함께 설계한다

source_id, revision, visibility, language처럼 정책에서 자주 읽는 정규화된 필드를 둔다. 사용자 입력과 무관하게 서버가 대상 문서의 권한 조건을 강제한다. 예시는 공개 문서만 검색하고 본문에 “변경”이 있는 후보를 고른다. [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) · [Chroma · Full Text Search](https://docs.trychroma.com/docs/querying-collections/full-text-search) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)

```python
import chromadb

collection = chromadb.EphemeralClient().create_collection("filter-demo", embedding_function=None)
collection.add(
    ids=["public", "private", "other"],
    documents=["배송 주소 변경", "관리자 주소 변경", "영수증 열람"],
    embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    metadatas=[{"visibility": "public"}, {"visibility": "private"}, {"visibility": "public"}],
)
rows = collection.query(
    query_embeddings=[[1.0, 0.0]],
    n_results=3,
    where={"visibility": "public"},
    where_document={"$contains": "변경"},
)
assert rows["ids"] == [["public"]]
```

## 2. 본문 필터와 순위 검색을 구분한다

문서 포함 조건은 필요한 용어가 있어야 할 때 쓴다. 어휘 관련성 점수로 순위를 만드는 전문 검색이나 하이브리드 랭킹은 별도 메커니즘을 구성한다. [Chroma · Full Text Search](https://docs.trychroma.com/docs/querying-collections/full-text-search) · [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html) · [Chroma Cloud · Hybrid Search](https://docs.trychroma.com/cloud/search-api/hybrid-search)
