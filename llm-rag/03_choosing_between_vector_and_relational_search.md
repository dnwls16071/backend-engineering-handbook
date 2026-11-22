# Choosing Between Vector and Relational Search

관계형 조건 조회, 전문 검색, 벡터 근접 검색은 업무에서 다른 질문에 답한다. 한 데이터베이스에서 이 기능을 함께 제공하는 구성도 있다. [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) · [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 1. 질문에 필요한 인덱스와 조건을 정한다

| 업무 | 먼저 사용할 조건 | 근거 |
| --- | --- | --- |
| 특정 주문 ID와 배송 상태 | 키 조회와 관계형 필터 | [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) · [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html) |
| 반품 정책에 포함된 정확한 용어 | 키워드와 전문 검색 | [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html) · [Chroma · Full Text Search](https://docs.trychroma.com/docs/querying-collections/full-text-search) |
| 유사한 자연어 문의나 관련 도움말 | 벡터 근접 검색과 문서 메타데이터 조건 | [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) |

## 2. 정본과 검색용 색인의 재동기화 경계를 정한다

원본 문서나 주문은 권한과 데이터 수명 주기를 관리하는 정본에 둔다. 검색용 청크·벡터는 원문 버전으로 추적하고 갱신·삭제 뒤 다시 맞출 수 있게 한다. 근사 검색을 고른 경우 동일한 질의에서 정확 검색 대비 재현율과 지연을 측정한다. [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) · [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) · [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
