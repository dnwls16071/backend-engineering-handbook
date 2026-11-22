# Diagnosing Vector Similarity Results

검색 결과의 품질을 판단하려면 한 건의 점수보다 어떤 후보가 빠졌고 왜 빠졌는지 본다. 동의어, 정확한 식별자, 답이 없는 질의를 각각 준비한다. [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html)

## 1. 표현·필터·색인 실패를 구분한다

1순위가 기대한 문서와 다르면 먼저 그 원문이 올바른 버전으로 색인됐는지 확인한다. 문서가 후보에 없으면 청킹이나 필터·임베딩을 확인하고, 정확 검색에는 있지만 HNSW 검색에서 빠졌다면 탐색 설정을 검토한다. [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)

## 2. 결과 계약과 임계값을 문서화한다

상위 거리와 정답 ID, 최종 인용을 따로 기록한다. 모델·거리 함수·청크 설계가 바뀌면 점수 임계값을 이전 설정에서 재사용하기 전에 새 평가셋에 대조한다. [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
