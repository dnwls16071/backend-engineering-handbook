# Evaluating Semantic Search with BGE-M3

BGE-M3의 dense 임베딩으로 질문과 후보 문서를 같은 벡터 공간에서 비교할 수 있다. 검색 순위는 사람이 지정한 관련 문서 라벨과 대조한다. [BAAI · BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3) · [Chen et al. · M3-Embedding](https://arxiv.org/abs/2402.03216) · [NIST · TREC Overview](https://trec.nist.gov/overview.html)

## 1. 코사인 유사도와 검색 순위를 확인한다

코사인 유사도는 두 벡터의 내적을 두 벡터 길이의 곱으로 나눈 값이다. L2 정규화한 벡터는 내적으로 같은 값을 얻는다. 영벡터를 받으면 예제에서는 잘못된 입력으로 기록하고, 동일 점수는 문서 ID 같은 고정 규칙으로 정렬한다. [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html)

공식 모델 카드의 BGEM3FlagModel과 encode 결과의 dense_vecs를 사용한다. 질의와 문서의 모델 리비전, 최대 길이와 절단 기준, 청크 분할을 기록한다. dense·sparse·multi-vector 모드를 섞을 경우 결합 방식도 변경 사항으로 관리한다. [BAAI · BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3) · [Chen et al. · M3-Embedding](https://arxiv.org/abs/2402.03216)

## 2. 정답 문서 라벨을 기준으로 비교한다

한 질의의 관련 청크가 4개이고 상위 5개에서 3개를 찾았다면 Recall@5는 3/4다. MRR은 첫 관련 청크 순위의 역수를 질의별로 평균하며, 없는 경우에는 0을 넣는다. 관련 문서가 없는 질의는 일반 Recall@K 계산에서 별도 분리해 보류 검증에 사용한다. 높은 유사도는 검색 후보를 정하는 신호로 쓰고, 답변의 근거 일치는 03번 기준으로 확인한다. [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [Chen et al. · M3-Embedding](https://arxiv.org/abs/2402.03216) · [ir-measures · Information Retrieval Measures](https://ir-measur.es/en/latest/measures.html)

아래 코드는 BGE-M3 순위 결과에 넣을 수 있는 지표 계산이다. 같은 문서 ID는 순위에 한 번만 들어간 것으로 가정한다. 관련 문서가 없는 케이스에서는 두 지표를 집계하지 않는다. [ir-measures · Information Retrieval Measures](https://ir-measur.es/en/latest/measures.html) · [NIST · TREC Overview](https://trec.nist.gov/overview.html)

```python
def retrieval_scores(ranked, relevant, k):
    if k < 1 or len(ranked) != len(set(ranked)):
        raise ValueError("expected positive k and unique document IDs")
    if not relevant:
        return None
    recall = len(set(ranked[:k]) & relevant) / len(relevant)
    reciprocal_rank = next(
        (1 / rank for rank, doc in enumerate(ranked, 1) if doc in relevant), 0.0
    )
    return recall, reciprocal_rank

assert retrieval_scores(["D9", "D1", "D2"], {"D1", "D2", "D3"}, 2) == (1 / 3, 0.5)
assert retrieval_scores(["D9"], {"D1"}, 5) == (0.0, 0.0)
assert retrieval_scores(["D9"], set(), 5) is None
```
