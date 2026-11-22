# Chunking Documents for a Semantic Search Demo

질문과 직접 대응하는 단락을 검색하려면 원문을 탐색 단위로 나눈다. 제목·문서 ID와 위치를 같이 보존한다. [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval) · [LangChain · Recursive Splitting](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)

## 1. 고정한 도움말의 청크를 만들어 검색한다

아래는 준비한 단락 세 개를 직접 임베딩하고, 문서와 출처를 포함한 검색 결과를 표시하는 작은 데모다. embeddinggemma를 준비하고 Python 가상환경에서 실행한다. 상위 순위는 모델과 입력에 따라 평가한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)

```python
from tempfile import TemporaryDirectory
import chromadb
from ollama import Client

ollama = Client(host="http://127.0.0.1:11434")
contents = [
    "배송지 변경 | 상품을 출고하기 전에 주문 내역에서 배송 주소를 수정할 수 있습니다.",
    "반품 신청 | 수령한 상품은 고객지원에서 반품 요청을 접수할 수 있습니다.",
    "영수증 | 주문 내역에서 영수증을 확인할 수 있습니다.",
]

def embed(texts):
    return ollama.embed(model="embeddinggemma", input=texts, truncate=False).embeddings

with TemporaryDirectory() as directory:
    client = chromadb.PersistentClient(path=directory)
    collection = client.create_collection(
        "help-demo", embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )
    collection.add(
        ids=["shipping#1", "returns#1", "receipt#1"],
        documents=contents,
        embeddings=embed(contents),
        metadatas=[{"source": s} for s in ("shipping", "returns", "receipt")],
    )
    result = collection.query(
        query_embeddings=embed(["받는 주소를 어디서 바꾸나요?"]),
        n_results=2,
        include=["documents", "metadatas", "distances"],
    )
    for row in zip(result["ids"][0], result["distances"][0],
                   result["metadatas"][0], result["documents"][0]):
        print(row)
```

## 2. 분할 기준과 검색 결과를 같이 조정한다

한 청크에 여러 정책이 섞이면 답의 위치를 찾기 어렵고, 너무 짧으면 예외 조건을 잃을 수 있다. 제목과 관련 단락을 먼저 보존하고, 필요할 때 크기와 겹침을 조금씩 바꿔 같은 질의로 비교한다. [LangChain · Recursive Splitting](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)
