# Tuning HNSW Graph and Search Parameters

HNSW의 그래프 밀도, 구성 탐색 폭, 질의 탐색 폭은 인덱스 비용과 재현율에 서로 다른 시점에서 영향을 준다. [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Chroma 1.5.5 · HNSW Configuration](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/api/collection_configuration.py)

## 1. 로컬 Chroma의 파라미터를 구분한다

| 설정 | 적용 시점 | 검증 포인트 | 근거 |
| --- | --- | --- | --- |
| max_neighbors (M) | 그래프 생성 | 노드 연결의 기준을 정한다. 구축 시간과 메모리 사용량을 본다. | [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) |
| ef_construction | 삽입과 그래프 생성 | 연결 후보를 탐색하는 폭이다. 색인 구축 시간과 재현율의 차이를 본다. | [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) |
| ef_search | 검색 | 검색 후보를 탐색하는 폭이다. 상위 k의 재현율과 p95 지연을 함께 본다. | [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Chroma 1.5.5 · HNSW Configuration](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/api/collection_configuration.py) |

## 2. 생성 옵션과 변경 가능한 옵션을 나눠 실습한다

다음은 Chroma 1.5.5에서 새 컬렉션을 만든 뒤 ef_search를 바꾸는 예다. M·거리·구성 탐색 폭을 바꾸는 실험은 새 컬렉션으로 구축한다. 비교는 같은 데이터·필터·질의와 정확 검색 top-k를 기준으로 한다. [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Chroma 1.5.5 · HNSW Configuration](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/api/collection_configuration.py) · [Malkov·Yashunin · HNSW](https://arxiv.org/abs/1603.09320) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html)

```python
import chromadb

client = chromadb.EphemeralClient()
collection = client.create_collection(
    "hnsw-demo", embedding_function=None,
    configuration={"hnsw": {
        "space": "cosine", "max_neighbors": 24,
        "ef_construction": 160, "ef_search": 64,
    }},
)
collection.modify(configuration={"hnsw": {"ef_search": 128}})
assert collection.configuration["hnsw"]["ef_search"] == 128
```
