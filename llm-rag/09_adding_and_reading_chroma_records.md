# Adding and Reading Chroma Records

add는 ID·벡터·문서·메타데이터를 함께 저장한다. get은 ID나 필터를 기준으로 읽는 API이며 거리 순위는 query에서 얻는다. [Chroma · Adding Data](https://docs.trychroma.com/docs/collections/add-data) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 1. 안정적인 문서 청크 ID를 적용한다

원문 ID와 리비전, 청크 위치를 기록하면 재색인 결과와 원문을 연결할 수 있다. 아래는 모델 다운로드 없이 두 벡터로 동작을 확인하는 독립 실습이다. [Chroma · Adding Data](https://docs.trychroma.com/docs/collections/add-data) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [LangChain · Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)

```python
import chromadb

client = chromadb.EphemeralClient()
collection = client.create_collection("record-demo", embedding_function=None)
collection.add(
    ids=["shipping-v1-01", "returns-v1-01"],
    embeddings=[[1.0, 0.0], [0.0, 1.0]],
    documents=["출고 전 배송지 변경", "수령 후 반품 신청"],
    metadatas=[{"topic": "shipping"}, {"topic": "returns"}],
)
row = collection.get(ids=["shipping-v1-01"], include=["documents", "metadatas"])
assert row["ids"] == ["shipping-v1-01"]
assert row["metadatas"][0]["topic"] == "shipping"
```

## 2. 동일 ID 재등록의 의도를 API에 드러낸다

신규 삽입과 갱신을 구분한다. 재실행 때 같은 ID를 최신 값으로 수렴시키는 인제스트에는 upsert를 사용하고, 처리 기록에는 원문 버전과 색인 결과를 함께 남긴다. [Chroma · Adding Data](https://docs.trychroma.com/docs/collections/add-data) · [Chroma · Updating Data](https://docs.trychroma.com/docs/collections/update-data)
