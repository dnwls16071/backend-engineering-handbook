# Querying Chroma and Interpreting Distances

query는 질의마다 가까운 레코드를 반환한다. 결과가 질의별 중첩 배열로 오므로 같은 인덱스의 ID·문서·메타데이터·거리를 함께 읽는다. [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure)

## 1. 코사인 거리의 순서를 확인한다

아래는 정규화된 합성 벡터 예제다. 결과는 similarity의 내림차순이 아니라 distance의 오름차순으로 해석한다. 쿼리 하나라도 반환 배열에는 질의 축이 있다. [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html)

```python
import math
import chromadb

client = chromadb.EphemeralClient()
collection = client.create_collection(
    "distance-demo", embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)
collection.add(
    ids=["parallel", "orthogonal"], embeddings=[[1.0, 0.0], [0.0, 1.0]],
    documents=["같은 방향", "직교 방향"],
)
result = collection.query(
    query_embeddings=[[1.0, 0.0]], n_results=2, include=["documents", "distances"],
)
assert result["ids"][0] == ["parallel", "orthogonal"]
assert math.isclose(result["distances"][0][0], 0.0, abs_tol=1e-6)
assert math.isclose(result["distances"][0][1], 1.0, abs_tol=1e-6)
```

## 2. 거리를 답변 정확도의 확률로 해석하지 않는다

거리는 특정 모델과 인덱스의 상대적인 근접도다. 관련성이 약한 후보도 상위 k개에 들어올 수 있다. 보류 임곗값이 필요하면 관련 없는 질문과 실제 정답 질의의 분포를 수집해 적용 범위를 정한다. [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
