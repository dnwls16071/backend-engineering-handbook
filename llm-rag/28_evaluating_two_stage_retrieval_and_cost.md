# Evaluating Two-Stage Retrieval and Cost

첫 단계 후보 수와 두 번째 단계가 남기는 개수를 따로 조정한다. 후보 회수율, 최종 순위, 부하와 비용을 한 실험표에 기록한다. [Sentence Transformers · Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Liu et al. · Lost in the Middle](https://arxiv.org/abs/2307.03172)

## 1. 단계마다 실패 원인과 지표를 설정한다

| 경계 | 측정 항목 | 근거 |
| --- | --- | --- |
| 후보 검색 | 정답이 후보에 있던 비율, Recall@m, 검색 지연 | [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Sentence Transformers · Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) |
| 재랭킹 | nDCG@k, MRR, 쌍 수와 재랭킹 지연 | [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Sentence Transformers · Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) |
| 생성 입력 | 실제 들어간 근거 수와 토큰, 답변·인용의 적합성 | [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) · [Liu et al. · Lost in the Middle](https://arxiv.org/abs/2307.03172) |

## 2. k 값과 비용을 단계별로 비교한다

대표 질의에서 후보 수 m을 여러 값으로 바꾸고 최종 k와 토큰 예산을 고정한다. 후보를 더 넣어도 순위와 답이 개선되지 않거나 p95가 목표를 넘는다면 후보 수·배치·입력 길이를 다시 조정한다. [Sentence Transformers · Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) · [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Liu et al. · Lost in the Middle](https://arxiv.org/abs/2307.03172)
