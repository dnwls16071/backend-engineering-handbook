# Connecting Ollama as a Chroma Embedding Function

Chroma의 OllamaEmbeddingFunction은 문서 또는 질의 문자열을 받아 Ollama의 embed 호출로 변환한다. Chroma 서버에 임베딩 모델 자체가 설치되는 구조와는 다르다. [Chroma 1.5.5 · Ollama Embedding Function](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/utils/embedding_functions/ollama_embedding_function.py) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 1. 문서와 질의 양쪽에 같은 함수를 적용한다

Ollama 서버와 모델을 켠 뒤 다음 코드를 실행한다. 이 자동 임베딩 예제는 뒤의 명시적 벡터 실습과 별도 컬렉션을 사용한다. [Chroma 1.5.5 · Ollama Embedding Function](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/utils/embedding_functions/ollama_embedding_function.py) · [Ollama · Embeddings](https://docs.ollama.com/capabilities/embeddings) · [Chroma · Clients](https://cookbook.chromadb.dev/core/clients/)

```python
from tempfile import TemporaryDirectory
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

embedding = OllamaEmbeddingFunction(
    url="http://127.0.0.1:11434", model_name="embeddinggemma", timeout=30,
)
with TemporaryDirectory() as directory:
    client = chromadb.PersistentClient(path=directory)
    collection = client.create_collection(
        "rag-auto-demo", embedding_function=embedding,
        configuration={"hnsw": {"space": "cosine"}},
    )
    collection.add(ids=["shipping-01"], documents=["출고 전에는 배송 주소를 변경할 수 있습니다."])
    result = collection.query(query_texts=["배송받을 주소를 고치고 싶어요"], n_results=1)
    assert result["ids"] == [["shipping-01"]]
```

## 2. 전처리와 잘림 정책을 어디서 적용할지 정한다

Chroma 1.5.5 내장 함수는 Ollama Python Client에 모델과 텍스트를 보낸다. truncate=False나 별도의 질의 전처리를 반드시 적용하려면 embed를 직접 호출해 결과를 embeddings와 query_embeddings로 전달한다. [Chroma 1.5.5 · Ollama Embedding Function](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/utils/embedding_functions/ollama_embedding_function.py) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)
