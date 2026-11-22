# Updating and Deleting Chroma Records

update는 기존 ID의 레코드를 수정하고, upsert는 기존 ID를 갱신하거나 없으면 추가한다. 원문이 바뀌면 문서와 그 문서에서 만든 벡터를 함께 수정한다. [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data) · [Chroma · Deleting Data](https://docs.trychroma.com/docs/collections/delete-data)

## 1. 명시적으로 벡터를 만드는 컬렉션의 수정 실습

이 예에서는 합성 벡터를 사용한다. 실제 서비스에서 본문이 바뀌면 같은 모델과 전처리로 임베딩을 다시 계산한다. 삭제는 지울 ID를 확인한 뒤 적용한다. [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data) · [Chroma · Deleting Data](https://docs.trychroma.com/docs/collections/delete-data) · [Ollama · Embeddings](https://docs.ollama.com/capabilities/embeddings)

```python
import chromadb

client = chromadb.EphemeralClient()
collection = client.create_collection("update-demo", embedding_function=None)
collection.upsert(ids=["shipping-01"], documents=["기존 안내"], embeddings=[[1.0, 0.0]])
collection.update(ids=["shipping-01"], documents=["수정된 안내"], embeddings=[[0.8, 0.6]])
assert collection.get(ids=["shipping-01"])["documents"] == ["수정된 안내"]
collection.delete(ids=["shipping-01"])
assert collection.get(ids=["shipping-01"])["ids"] == []
```

## 2. 원문 삭제를 검색에도 반영한다

문서가 철회되거나 버전이 바뀌면 원문에 연결된 모든 청크를 찾아 삭제하거나 활성 버전에서 제외한다. 필터로 대량 삭제할 때는 먼저 같은 필터로 대상과 건수를 확인하고, 색인 복구 기준을 유지한다. [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Chroma · Deleting Data](https://docs.trychroma.com/docs/collections/delete-data) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
