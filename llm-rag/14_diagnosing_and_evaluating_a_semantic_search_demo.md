# Diagnosing and Evaluating a Semantic Search Demo

검색 데모를 다듬을 때 질의, 기대 청크, 실제 순위, 점수, 검색에 적용한 필터를 함께 기록한다. [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Chroma · Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get) · [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)

## 1. 같은 평가셋에서 Recall과 순위를 구한다

보통 Recall@k는 관련 청크 중 상위 k개에 포함된 비율이다. 첫 정답 순위가 중요한 경우 MRR을, 여러 관련 문서의 순위와 등급이 중요하면 nDCG를 함께 본다. 정답이 없는 질문은 보류 사례로 별도 집계한다. [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)

## 2. 한 번에 바꾼 요소와 실패 패턴을 남긴다

raw 질의와 검색 후보 목록을 기준으로 청킹 또는 k를 하나씩 바꾼다. 권한 필터로 제외된 정답, 이웃 후보 부족, 생성 단계 누락을 별도 원인으로 분류한다. 통합 평가는 검색 성공과 근거 있는 답변 성공을 나눠 수집한다. [ir-measures · Retrieval Metrics](https://ir-measur.es/en/latest/measures.html) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html) · [Lewis et al. · Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
