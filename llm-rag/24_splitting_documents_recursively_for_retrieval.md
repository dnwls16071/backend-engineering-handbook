# Splitting Documents Recursively for Retrieval

재귀 분할은 먼저 큰 구조 경계를 사용하고, 크기 제한을 넘는 부분에만 더 작은 구분자를 적용한다. [LangChain · Recursive Splitting](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)

## 1. 구분자 순서와 길이 단위를 명시한다

예를 들어 제목이나 문단 경계, 줄바꿈, 공백, 마지막 문자 경계 순으로 분할한다. LangChain의 기본 길이 함수는 문자 수를 셀 수 있다. 실제 모델 입력 한도를 맞출 때는 해당 토크나이저를 길이 기준으로 맞추거나 임베딩 요청에서 초과를 검출한다. [LangChain · Recursive Splitting](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Google · EmbeddingGemma Model Card](https://huggingface.co/google/embeddinggemma-300m)

## 2. 겹침은 경계에서 잃은 정보를 보완하는 데 사용한다

경계를 넘는 조건을 보존하려고 일부 겹치게 할 수 있다. 같은 내용이 상위 후보를 반복해서 채우거나 인덱스가 과하게 커지는지도 확인한다. 한국어와 다국어 문서는 문장·문단 경계와 구두점 처리를 대표 문서에서 검증한다. [LangChain · Recursive Splitting](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
