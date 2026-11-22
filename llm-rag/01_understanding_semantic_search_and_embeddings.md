# Understanding Semantic Search and Embeddings

의미 기반 검색은 질문과 문서에서 벡터를 만들고 가까운 문서를 후보로 찾는다. 고객이 “배송지 변경” 대신 “받는 주소를 바꾸고 싶어요”라고 표현해도 관련 도움말이 검색되는지 확인한다. [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)

## 1. 임베딩이 찾는 것과 생성 단계가 하는 일을 구분한다

임베딩은 학습한 표현을 검색에 쓰는 벡터다. 검색 결과는 관련 후보라서 본문이 실제 답을 지지하는지 검사해야 한다. RAG는 검색 결과를 모델의 입력으로 전달하고 질문에 맞는 답과 근거를 생성한다. [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)

## 2. 의미와 글자 그대로의 일치를 함께 검증한다

동의어 질문은 벡터 검색에서 먼저 보고, 오류 코드나 상품 코드처럼 표기가 중요한 질문은 키워드 기준도 둔다. 원문의 버전과 출처를 보관해야 검색 결과를 사람이 검증할 수 있다. [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [PostgreSQL 18 · Full Text Search](https://www.postgresql.org/docs/18/textsearch-intro.html) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)

## 3. 주제별로 이어 읽기

[Ollama 준비](05_running_ollama_locally.md), [Chroma 컬렉션](07_managing_persistent_chroma_collections.md), [첫 검색 데모](13_chunking_documents_for_a_semantic_search_demo.md), [Express API](20_building_an_ai_search_api_with_express.md), [RAG 인제스트](21_building_a_rag_ingestion_pipeline.md), [고급 검색](27_reranking_candidates_with_cross_encoders.md) 순서로 연결한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Clients](https://cookbook.chromadb.dev/core/clients/) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) · [Sentence Transformers · Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
