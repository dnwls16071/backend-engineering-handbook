# Comparing Chroma with Other Vector Stores

벡터 저장소는 유사도 검색 기능 외에 정본과의 거리, 필터·검색 방식, 운영 비용이 다르다. 같은 벡터·필터·질의로 비교한다. [Chroma · Architecture](https://docs.trychroma.com/reference/architecture/overview) · [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) · [Qdrant · Collections](https://qdrant.tech/documentation/manage-data/collections/) · [Elastic · kNN Search](https://www.elastic.co/docs/solutions/search/vector/knn)

## 1. 후보마다 운영 모델을 확인한다

| 선택 | 대표 설계와 보는 조건 | 근거 |
| --- | --- | --- |
| Chroma | 컬렉션 추상화, Python 로컬 및 HTTP 모드. 로컬과 분산의 기능·운영 계약을 따로 본다. | [Chroma · Architecture](https://docs.trychroma.com/reference/architecture/overview) · [Chroma · Clients](https://cookbook.chromadb.dev/core/clients/) · [Chroma · Client-Server Mode](https://docs.trychroma.com/docs/run-chroma/client-server) |
| pgvector | PostgreSQL의 타입·SQL 필터와 정확·근사 검색을 함께 사용한다. 원본 쿼리의 부하와 인덱스 선택을 본다. | [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) |
| Qdrant | 컬렉션과 벡터·payload를 결합한다. 이름 있는 복수 벡터의 저장과 검색이 필요한지 본다. | [Qdrant · Collections](https://qdrant.tech/documentation/manage-data/collections/) |
| Elasticsearch | 기존 키워드 검색과 벡터 검색을 조합한다. 문서 매핑·필터·결합 비용을 본다. | [Elastic · kNN Search](https://www.elastic.co/docs/solutions/search/vector/knn) |

## 2. 비교 목표와 검증 데이터를 고정한다

관련성 Recall@k, 상위 지연, 업데이트 반영 시간, 삭제 조건, 백업·복구를 같이 비교한다. 요약표의 기능은 제품의 모드와 적용 버전에 맞춰 확인하며, 벡터 수와 조회 패턴에 맞춘 실측으로 결정한다. [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [pgvector · Indexing and Distances](https://github.com/pgvector/pgvector) · [Qdrant · Collections](https://qdrant.tech/documentation/manage-data/collections/) · [Elastic · kNN Search](https://www.elastic.co/docs/solutions/search/vector/knn)
