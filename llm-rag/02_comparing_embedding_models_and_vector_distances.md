# Comparing Embedding Models and Vector Distances

텍스트를 임베딩하는 인코더는 학습 목표에 맞게 가까워질 표현을 만든다. 저장한 문서와 질문은 호환되는 같은 모델·리비전과 검색용 입력 전처리로 인코딩한다. [Reimers·Gurevych · Sentence-BERT](https://arxiv.org/abs/1908.10084) · [Google · EmbeddingGemma Model Card](https://huggingface.co/google/embeddinggemma-300m) · [Ollama · Embeddings](https://docs.ollama.com/capabilities/embeddings)

## 1. 거리의 정의와 방향을 확인한다

| 선택 | 의미 | 검색 결과를 읽는 법 | 근거 |
| --- | --- | --- | --- |
| cosine | Chroma는 1에서 코사인 유사도를 뺀 거리 | 같은 방향일수록 0에 가깝다. | [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) |
| l2 | Chroma의 제곱 L2 거리 | 같은 벡터는 0이다. 제곱근을 취한 거리와 순위는 같다. | [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) |
| ip | Chroma에서는 1에서 내적을 뺀 거리 | 정규화하지 않으면 벡터 크기도 순위에 영향을 준다. | [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) |

## 2. 정규화와 거리 기준값을 확인한다

모든 벡터가 L2 단위 벡터라면 코사인, 내적, 제곱 L2의 순위 관계가 일치한다. 서로 다른 모델이나 거리 함수의 점수 범위는 별도로 검증한다. 너무 짧거나 비어 있는 입력과 처리 불가한 벡터는 색인 전에 걸러낸다. [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed)
