# Building a RAG Ingestion Pipeline

인제스트는 원문에서 청크를 만들고 임베딩과 출처를 색인한다. 문서 검색·생성 요청은 별도 API에서 같은 모델과 컬렉션을 사용한다. [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval) · [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed)

## 1. 서버 모드에서 재실행 가능한 인제스트를 실행한다

같은 Python 환경에서 별도 셸의 chroma run을 시작한다. 아래 seed_help.py는 가상의 도움말과 비공개 문서를 한 번에 색인한다. 청크 ID는 원문과 버전·위치를 반영한다. 이 샘플은 모든 청크가 짧고 작으므로 한 배치로 보낸다. [Chroma · Client-Server Mode](https://docs.trychroma.com/docs/run-chroma/client-server) · [Chroma · Adding Data](https://docs.trychroma.com/docs/collections/add-data) · [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data) · [Chroma · Batching](https://cookbook.chromadb.dev/strategies/batching/)

```bash
chroma run --path ./rag-server-data --host 127.0.0.1 --port 8000
```

```python
# seed_help.py
import os
import chromadb
from ollama import Client

client = chromadb.HttpClient(host="127.0.0.1", port=int(os.getenv("CHROMA_PORT", "8000")))
model = Client(host=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
collection = client.get_or_create_collection(
    "rag-help-v1", embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)
rows = [
    ("shipping-v1#1", "출고 전에는 주문 내역에서 배송 주소를 수정할 수 있습니다.", "도움말/배송", "public"),
    ("returns-v1#1", "수령 후 반품은 고객지원에서 신청할 수 있습니다.", "도움말/반품", "public"),
    ("internal-v1#1", "배송 주소 업무 검토는 내부 문서에서 진행합니다.", "내부/배송", "private"),
]
texts = [text for _, text, _, _ in rows]
vectors = model.embed(model="embeddinggemma", input=texts, truncate=False).embeddings
collection.upsert(
    ids=[key for key, _, _, _ in rows],
    embeddings=vectors,
    documents=texts,
    metadatas=[{"source": source, "visibility": visibility}
               for _, _, source, visibility in rows],
)
print(collection.id)
```

## 2. 모델 설정과 실행 환경을 확인한다

Express 실습 디렉터리에서 seed_help.py를 실행해 컬렉션 ID를 환경 변수에 넣는다. 생성에는 같은 Ollama 서버에 별도의 채팅 모델을 설치한다. 앱이 로컬에서 제공하는 요청만 테스트한다. [Chroma · Client-Server Mode](https://docs.trychroma.com/docs/run-chroma/client-server) · [Ollama · embeddinggemma](https://ollama.com/library/embeddinggemma) · [Ollama · qwen2.5](https://ollama.com/library/qwen2.5) · [Ollama · Generate a Chat Message](https://docs.ollama.com/api/chat) · [Express 5 · API](https://expressjs.com/en/5x/api/)

```bash
ollama pull qwen2.5:1.5b
export CHROMA_COLLECTION_ID="$(python seed_help.py)"
node search.cjs
```

## 3. 재수집과 삭제를 처리한다

업무 문서가 변경되면 기존 원문 버전과의 차이를 비교해 새 청크를 올리고 없어진 청크를 삭제한다. 모델이나 차원·거리 함수가 바뀌면 새 컬렉션을 만든다. 새 버전의 적재를 검증한 뒤 검색·생성 경로를 함께 전환한다. [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data) · [Chroma · Deleting Data](https://docs.trychroma.com/docs/collections/delete-data) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Ollama · Embeddings](https://docs.ollama.com/capabilities/embeddings)
