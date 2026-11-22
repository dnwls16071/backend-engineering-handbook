# Batching Indexing and Measuring Search Performance

임베딩 호출, 벡터 저장, 검색, 응답 조합은 서로 다른 병목을 갖는다. 배치와 페이징은 각 API가 제공하는 계약을 구분해 적용한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Batching](https://cookbook.chromadb.dev/strategies/batching/) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 1. 쓰기 배치와 읽기 페이징을 분리한다

Ollama에는 입력 배열을 보내고 Chroma 측 배치는 클라이언트의 get_max_batch_size 이하로 나눈다. get의 limit·offset은 일반 레코드 목록에 사용한다. Python query의 n_results는 상위 k개 요청 크기다. 안정적인 사용자 검색 페이지가 필요하면 순위 결과의 ID 목록과 세션 범위를 유지한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Batching](https://cookbook.chromadb.dev/strategies/batching/) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 2. 확장 전후를 동일한 워크로드로 측정한다

준비 실행 후 p50·p95와 실패율을 기록한다. 벡터 수, 차원, k, 필터 선택도, 동시 사용자 수와 반환 필드를 고정해 비교한다. 전체 시간을 임베딩·검색·직렬화로 나눠 보고 지연·재현율·메모리 제한을 함께 본다. [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)
